# README film preview

The README combines an original SVG brand cover linked to the full film with a
collapsible native GitHub video attachment. The preview is the complete R52 film,
re-encoded at 1280×720, 30 fps, H.264/AAC. It is 9,458,094 bytes and 142.144 seconds.
The 1080p version and selectable English captions remain on
[YouTube](https://youtu.be/Dbbt4qoKmiI).

- [GitHub preview attachment](https://github.com/user-attachments/assets/072470db-3bcf-4769-8c83-fcb15753ef5e)
- Preview SHA-256: `0ac72ec451b62d4802a8a8553d3311c2ac7e4a6894a164830c29a6696285fe12`
- Source master SHA-256: `7492657b300227294b89b0608183d9b87641d7ea664bd35b852fca3c8eb94e99`
- Encoding: two-pass libx264, 440 kb/s video, Lanczos 1280×720 scaling,
  `yuv420p`, AAC 80 kb/s at 48 kHz, MP4 fast-start. No picture edit or retiming.
- Verification: full local decode passed. GitHub's actual Markdown preview rendered
  a native player; authenticated playback progressed with 1280×720 decoded frames.
  Dense code is best viewed in the 1080p film or in the workbench.

The repository is public. The original attachment was uploaded during private
review and did not become anonymously readable after publication. A replacement
was uploaded in the public repository context. Anonymous access is being checked
as part of the [publication record](publication-round55.md).
The film is hosted as an attachment, not committed as a large binary into the code tree.

## Media credits

The software's Apache-2.0 license does not relicense third-party film media.
Music: “House Vibez” by Lily J, under the
[Mixkit Stock Music Free License](https://mixkit.co/license/modal/musicFree/).
Sound effects: [Mixkit Sound Effects Free License](https://mixkit.co/license/modal/sfxFree/).
Music and effects are included in the finished audiovisual work; raw assets are
not distributed in this repository. Concept imagery uses MiniMax-H3 and is
illustrative, not a recorded GPU execution. Narration is synthetic; the native
voice engine is undisclosed. Original animation and branding by this project.
The film's end credits and YouTube description retain these attributions.
