// New Warp Relay harness. Loads the unchanged public PTX or a recorded candidate.
// The math reference is independent CPU long-double arithmetic, not device code.
#include <cuda.h>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <limits>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

constexpr int ROWS=2, COLS=1024, THREADS=256, SHARED=1024, GUARD=64;
constexpr double NORM_RTOL=2e-6, NORM_ATOL=1e-7;
constexpr int OUTPUT_MAX_ULP=1, GRAPH_NODES=100, SAMPLES=31;

void check(CUresult value, const char* operation) {
    if (value == CUDA_SUCCESS) return;
    const char* name=nullptr; cuGetErrorName(value, &name);
    throw std::runtime_error(std::string(operation)+": "+(name ? name : "unknown CUDA error"));
}
#define CUDA(call) check((call), #call)

std::string quoted(const std::string& s) {
    std::string out="\"";
    for (unsigned char c:s) {
        if(c=='"' || c=='\\') { out+='\\'; out+=c; }
        else if(c<32) out+=' ';
        else out+=c;
    }
    return out+'"';
}

uint16_t bf16(float x) {
    uint32_t b; std::memcpy(&b,&x,4);
    if ((b & 0x7fffffffU)>0x7f800000U) return uint16_t((b>>16)|0x40);
    return uint16_t((b+0x7fffU+((b>>16)&1U))>>16);
}
float from_bf16(uint16_t x) {
    uint32_t b=uint32_t(x)<<16; float value; std::memcpy(&value,&b,4); return value;
}
int ordered(uint16_t b) { return b&0x8000 ? 0x8000-int(b&0x7fff) : 0x8000+int(b); }

struct Case { std::string name; std::vector<uint16_t> v,g; };
std::vector<Case> cases() {
    std::vector<Case> result;
    for(int seed=0;seed<32;seed++) {
        Case c{"random_"+std::to_string(seed),std::vector<uint16_t>(ROWS*COLS),{bf16(0.75f),bf16(-1.5f)}};
        std::mt19937 rng(1701+seed);
        // Explicit integer mapping makes inputs reproducible across C++ libraries.
        for(auto& x:c.v) x=bf16((int(rng()%20001)-10000)/1024.0f);
        result.push_back(c);
    }
    for(const std::string name:{"ones","alternating","impulse","tiny","large","zero_gain","zero_norm"}) {
        Case c{name,std::vector<uint16_t>(ROWS*COLS),{bf16(1.0f),bf16(-0.5f)}};
        for(int i=0;i<ROWS*COLS;i++) {
            float value=1;
            if(name=="alternating") value=(i%2 ? -1.f : 1.f)*(1+(i%7));
            if(name=="impulse") value=(i%COLS==513 ? 3.f : 0.f);
            if(name=="tiny") value=(i%2 ? -1.f : 1.f)*1e-10f;
            if(name=="large") value=(i%2 ? -1.f : 1.f)*1e10f;
            if(name=="zero_norm") value=0;
            c.v[i]=bf16(value);
        }
        if(name=="zero_gain") c.g={bf16(0),bf16(0)};
        result.push_back(c);
    }
    return result;
}

struct Reference { std::vector<uint16_t> w; std::vector<double> norms; };
Reference reference(const Case& c) {
    Reference ref{std::vector<uint16_t>(ROWS*COLS),std::vector<double>(ROWS)};
    for(int row=0;row<ROWS;row++) {
        long double sum=0;
        for(int j=0;j<COLS;j++) { long double v=from_bf16(c.v[row*COLS+j]); sum+=v*v; }
        long double norm=std::sqrt(sum); ref.norms[row]=double(norm);
        for(int j=0;j<COLS;j++) {
            long double v=from_bf16(c.v[row*COLS+j]);
            float value=norm==0 ? std::numeric_limits<float>::quiet_NaN() : float(v*from_bf16(c.g[row])/norm);
            ref.w[row*COLS+j]=bf16(value);
        }
    }
    return ref;
}

struct Buffer {
    CUdeviceptr allocation=0; size_t size;
    explicit Buffer(size_t bytes):size(bytes) { CUDA(cuMemAlloc(&allocation,size+2*GUARD)); }
    ~Buffer() { if(allocation) cuMemFree(allocation); }
    CUdeviceptr pointer() const { return allocation+GUARD; }
    void upload(const void* payload) {
        std::vector<uint8_t> bytes(size+2*GUARD,0xa5);
        std::memcpy(bytes.data()+GUARD,payload,size);
        CUDA(cuMemcpyHtoD(allocation,bytes.data(),bytes.size()));
    }
    std::vector<uint8_t> read(bool& guards_ok) const {
        std::vector<uint8_t> bytes(size+2*GUARD); CUDA(cuMemcpyDtoH(bytes.data(),allocation,bytes.size()));
        for(int j=0;j<GUARD;j++) guards_ok &= bytes[j]==0xa5 && bytes[GUARD+size+j]==0xa5;
        return std::vector<uint8_t>(bytes.begin()+GUARD,bytes.begin()+GUARD+size);
    }
};

struct Kernel {
    CUmodule module=nullptr; CUfunction function=nullptr;
    Kernel(const char* ptx,const char* entry) { CUDA(cuModuleLoad(&module,ptx)); CUDA(cuModuleGetFunction(&function,module,entry)); }
    ~Kernel() { if(module) cuModuleUnload(module); }
};

struct Workload {
    Buffer w{ROWS*COLS*2}, norms{ROWS*4}, v{ROWS*COLS*2}, g{ROWS*2};
    CUdeviceptr wp=w.pointer(), np=norms.pointer(), vp=v.pointer(), gp=g.pointer();
    int row_size=COLS; void* args[5]={&wp,&np,&vp,&gp,&row_size};
    void initialize(const Case& c) {
        std::vector<uint16_t> poison_w(ROWS*COLS,0x7fc1);
        float poison_n[ROWS]={std::numeric_limits<float>::quiet_NaN(),std::numeric_limits<float>::quiet_NaN()};
        w.upload(poison_w.data()); norms.upload(poison_n); v.upload(c.v.data()); g.upload(c.g.data());
    }
    void launch(const Kernel& k,CUstream stream=nullptr) { CUDA(cuLaunchKernel(k.function,ROWS,1,1,THREADS,1,1,SHARED,stream,args,nullptr)); }
};

bool correctness(Kernel& kernel, bool quick) {
    Workload work; bool all_pass=true; auto inputs=cases();
    if(quick) inputs.resize(1);
    for(const auto& input:inputs) {
        Reference expected=reference(input); int max_ulp=0, bit_differences=0, mismatches=0;
        double max_norm_relative=0; bool guards=true, input_preserved=true;
        int repeats=quick ? 1 : 3;
        for(int repeat=0;repeat<repeats;repeat++) {
            work.initialize(input); work.launch(kernel); CUDA(cuCtxSynchronize());
            auto wb=work.w.read(guards), nb=work.norms.read(guards), vb=work.v.read(guards), gb=work.g.read(guards);
            input_preserved &= std::memcmp(vb.data(),input.v.data(),vb.size())==0 && std::memcmp(gb.data(),input.g.data(),gb.size())==0;
            for(int j=0;j<ROWS*COLS;j++) {
                uint16_t actual; std::memcpy(&actual,wb.data()+2*j,2);
                float a=from_bf16(actual), e=from_bf16(expected.w[j]);
                if(std::isnan(e)) { if(!std::isnan(a)) mismatches++; continue; }
                if(!std::isfinite(a)) { mismatches++; continue; }
                int ulp=std::abs(ordered(actual)-ordered(expected.w[j]));
                max_ulp=std::max(max_ulp,ulp); bit_differences+=actual!=expected.w[j];
                if(ulp>OUTPUT_MAX_ULP) mismatches++;
            }
            for(int row=0;row<ROWS;row++) {
                float actual; std::memcpy(&actual,nb.data()+4*row,4);
                double error=std::abs(actual-expected.norms[row]);
                double relative=error/std::max(expected.norms[row],1e-30);
                if(std::isfinite(relative)) max_norm_relative=std::max(max_norm_relative,relative);
                if(!std::isfinite(actual) || error>NORM_ATOL+NORM_RTOL*std::abs(expected.norms[row])) mismatches++;
            }
        }
        bool pass=mismatches==0 && guards && input_preserved; all_pass &= pass;
        std::cout<<"{\"kind\":\"case\",\"name\":"<<quoted(input.name)<<",\"repeats\":"<<repeats
          <<",\"passed\":"<<(pass?"true":"false")<<",\"mismatches\":"<<mismatches<<",\"max_output_bf16_ulp\":"<<max_ulp
          <<",\"output_bit_differences\":"<<bit_differences<<",\"max_norm_relative_error\":"<<max_norm_relative
          <<",\"guards_intact\":"<<(guards?"true":"false")<<",\"inputs_unchanged\":"<<(input_preserved?"true":"false")<<"}\n";
    }
    std::cout<<"{\"kind\":\"correctness_summary\",\"passed\":"<<(all_pass?"true":"false")<<",\"cases\":"<<inputs.size()<<"}\n";
    return all_pass;
}

struct Graph {
    CUgraph graph=nullptr; CUgraphExec executable=nullptr;
    Graph(Workload& work,Kernel& kernel,CUstream stream) {
        CUDA(cuStreamBeginCapture(stream,CU_STREAM_CAPTURE_MODE_GLOBAL));
        for(int j=0;j<GRAPH_NODES;j++) work.launch(kernel,stream);
        CUDA(cuStreamEndCapture(stream,&graph)); CUDA(cuGraphInstantiateWithFlags(&executable,graph,0));
    }
    ~Graph() { if(executable) cuGraphExecDestroy(executable); if(graph) cuGraphDestroy(graph); }
};

void benchmark(Kernel& baseline,Kernel& candidate) {
    Workload work; work.initialize(cases()[0]); CUstream stream=nullptr;
    CUDA(cuStreamCreate(&stream,CU_STREAM_NON_BLOCKING));
    CUevent start=nullptr,end=nullptr; CUDA(cuEventCreate(&start,CU_EVENT_DEFAULT)); CUDA(cuEventCreate(&end,CU_EVENT_DEFAULT));
    {
        // Load functions and warm data before capture and before any timing.
        for(int j=0;j<100;j++) { work.launch(baseline,stream); work.launch(candidate,stream); }
        CUDA(cuStreamSynchronize(stream));
        Graph graphs[2]={{work,baseline,stream},{work,candidate,stream}};
        for(auto& graph:graphs) { CUDA(cuGraphUpload(graph.executable,stream)); CUDA(cuGraphLaunch(graph.executable,stream)); }
        CUDA(cuStreamSynchronize(stream));
        for(int sample=0;sample<SAMPLES;sample++) {
            double microseconds[2];
            for(int order=0;order<2;order++) {
                int which=(order+sample)%2; float milliseconds=0;
                CUDA(cuEventRecord(start,stream)); CUDA(cuGraphLaunch(graphs[which].executable,stream));
                CUDA(cuEventRecord(end,stream)); CUDA(cuEventSynchronize(end));
                CUDA(cuEventElapsedTime(&milliseconds,start,end)); microseconds[which]=milliseconds*1000.0/GRAPH_NODES;
            }
            std::cout<<"{\"kind\":\"timing_pair\",\"sample\":"<<sample<<",\"first\":"<<quoted(sample%2?"candidate":"baseline")
              <<",\"baseline_us\":"<<microseconds[0]<<",\"candidate_us\":"<<microseconds[1]<<"}\n";
        }
    }
    CUDA(cuEventDestroy(start)); CUDA(cuEventDestroy(end)); CUDA(cuStreamDestroy(stream));
}

int main(int argc,char** argv) {
    std::cout<<std::setprecision(12)<<std::unitbuf;
    CUcontext context=nullptr;
    try {
        if(argc==2 && std::string(argv[1])=="self-test") {
            if(bf16(1.0f)!=0x3f80 || bf16(1.00390625f)!=0x3f80 || bf16(1.01171875f)!=0x3f82 || from_bf16(0xbf80)!=-1.0f)
                throw std::runtime_error("BF16 round-to-nearest-even self-test failed");
            auto c=cases(); auto r=reference(c[32]);
            if(r.norms[0]!=32 || from_bf16(r.w[0])!=0.03125f) throw std::runtime_error("reference self-test failed");
            std::cout<<"{\"kind\":\"host_self_test\",\"passed\":true}\n"; return 0;
        }
        if(argc!=5) throw std::runtime_error("usage: runner check|quick|benchmark BASELINE_PTX ENTRY CANDIDATE_PTX");
        std::string mode=argv[1];
        if(mode!="check" && mode!="quick" && mode!="benchmark") throw std::runtime_error("unknown mode");
        CUDA(cuInit(0)); CUdevice device; CUDA(cuDeviceGet(&device,0)); int major,minor,driver;
        CUDA(cuDeviceGetAttribute(&major,CU_DEVICE_ATTRIBUTE_COMPUTE_CAPABILITY_MAJOR,device));
        CUDA(cuDeviceGetAttribute(&minor,CU_DEVICE_ATTRIBUTE_COMPUTE_CAPABILITY_MINOR,device));
        if(major!=10 || minor!=0) throw std::runtime_error("This unchanged sm_100a PTX requires the matching SM100 device; no retargeting allowed");
        char name[256]; CUDA(cuDeviceGetName(name,sizeof(name),device)); CUDA(cuDriverGetVersion(&driver));
        CUDA(cuCtxCreate(&context,nullptr,0,device));
        std::cout<<"{\"kind\":\"environment\",\"gpu\":"<<quoted(name)<<",\"compute_capability\":["<<major<<","<<minor<<"],\"cuda_driver_api\":"<<driver
          <<",\"grid\":[2,1,1],\"block\":[256,1,1],\"shared_bytes\":1024,\"norm_rtol\":"<<NORM_RTOL<<",\"norm_atol\":"<<NORM_ATOL
          <<",\"max_output_bf16_ulp_allowed\":"<<OUTPUT_MAX_ULP<<",\"graph_nodes\":"<<GRAPH_NODES<<",\"timing_samples\":"<<SAMPLES<<"}\n";
        bool passed=true;
        {
            Kernel baseline(argv[2],argv[3]);
            if(mode=="benchmark") { Kernel candidate(argv[4],argv[3]); benchmark(baseline,candidate); }
            else passed=correctness(baseline,mode=="quick");
        }
        CUDA(cuCtxDestroy(context)); context=nullptr;
        return passed ? 0 : 2;
    } catch(const std::exception& e) {
        std::cout<<"{\"kind\":\"error\",\"message\":"<<quoted(e.what())<<"}\n";
        if(context) cuCtxDestroy(context);
        return 1;
    }
}
