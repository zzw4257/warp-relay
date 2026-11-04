import {renderInspection,renderRunning,renderActivity,renderScope} from './inspection.mjs';
import {mountCode} from './code-view.mjs';
import {mountLibrary,mountInvestigation} from './case-library.mjs';
import {mountKernelWorkspace} from './kernel-workspace.mjs';
import {mountFlow} from './flow-view.mjs';
import {mountRunWorkspace} from './run-workspace.mjs';
window.WarpUI={mountRunWorkspace,mountFlow,mountKernelWorkspace,mountLibrary,mountInvestigation,renderInspection,renderRunning,renderActivity,renderScope,mountCode};
window.dispatchEvent(new Event('warp-ui-ready'));
