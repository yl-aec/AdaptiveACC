import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { IFCLoader } from 'web-ifc-three/IFCLoader';

// Three.js scene setup
let scene, camera, renderer, controls;
let currentModel = null;
let ifcLoader = null;

const canvas = document.getElementById('three-canvas');
const overlay = document.getElementById('viewer-overlay');
const fileInput = document.getElementById('ifc_file');
const placeholder = document.getElementById('preview-placeholder');
const fileInfo = document.getElementById('file-info');
const fileNameDisplay = document.getElementById('file-name-display');
const fileSizeDisplay = document.getElementById('file-size-display');
const reuploadBtn = document.getElementById('reupload-btn');
const exampleIfcBtn = document.getElementById('example-ifc-btn');
const regulationInput = document.getElementById('regulation');
const exampleRegulationBtn1 = document.getElementById('example-regulation-btn-1');
const exampleRegulationBtn2 = document.getElementById('example-regulation-btn-2');
const exampleRegulationText1 = 'Egress doors shall be of the pivoted or side-hinged swinging type.';
const exampleRegulationText2 = 'Where elevators are provided in buildings four or more stories above, or four or more stories below, grade plane, not fewer than one elevator shall provided access to all floors.';
const exampleIfcFileName = 'M02_no_space.ifc';
const exampleIfcPath = `/examples/ifc/${exampleIfcFileName}`;
const isLowPerfDevice = window.matchMedia('(max-width: 900px), (pointer: coarse)').matches;

function getRenderPixelRatio() {
    const maxRatio = isLowPerfDevice ? 1 : 1.5;
    return Math.min(window.devicePixelRatio || 1, maxRatio);
}

function getExampleIfcUrls() {
    const urls = [exampleIfcPath];
    const fallbackOrigin = `${window.location.protocol}//${window.location.hostname}:8000`;
    if (window.location.origin !== fallbackOrigin) {
        urls.push(`${fallbackOrigin}${exampleIfcPath}`);
    }
    return Array.from(new Set(urls));
}

async function fetchExampleIfcFile() {
    const urls = getExampleIfcUrls();
    let lastError = null;

    for (const url of urls) {
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`Request failed (${response.status})`);
            }
            return await response.blob();
        } catch (error) {
            lastError = error;
            console.warn('Example IFC fetch failed:', url, error);
        }
    }

    throw lastError || new Error('Failed to load example IFC model.');
}

// Initialize Three.js scene
function initViewer() {
    // Scene
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1a1a);

    // Camera
    const aspect = canvas.clientWidth / canvas.clientHeight;
    camera = new THREE.PerspectiveCamera(75, aspect, 0.1, 2000);
    camera.position.set(5, 5, 5);

    // Renderer
    renderer = new THREE.WebGLRenderer({
        canvas,
        antialias: !isLowPerfDevice,
        powerPreference: isLowPerfDevice ? 'low-power' : 'high-performance'
    });
    renderer.setSize(canvas.clientWidth, canvas.clientHeight);
    renderer.setPixelRatio(getRenderPixelRatio());

    // Enhanced lighting for better visibility
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
    scene.add(ambientLight);

    const directionalLight1 = new THREE.DirectionalLight(0xffffff, 1.0);
    directionalLight1.position.set(10, 10, 10);
    scene.add(directionalLight1);

    const directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.6);
    directionalLight2.position.set(-10, 10, -10);
    scene.add(directionalLight2);

    const directionalLight3 = new THREE.DirectionalLight(0xffffff, 0.4);
    directionalLight3.position.set(0, -10, 0);
    scene.add(directionalLight3);

    // Grid
    const gridHelper = new THREE.GridHelper(20, 20, 0x444444, 0x222222);
    scene.add(gridHelper);

    // Initialize IFC Loader
    ifcLoader = new IFCLoader();
    // Use different paths for dev and production
    const wasmPath = import.meta.env.DEV
        ? '/node_modules/web-ifc/'
        : '/wasm/';
    ifcLoader.ifcManager.setWasmPath(wasmPath);

    // Controls
    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.target.set(0, 0, 0);

    // Handle window resize
    window.addEventListener('resize', onWindowResize);

    // Start animation loop
    animate();

    console.log('Three.js viewer initialized successfully');
}

function onWindowResize() {
    const aspect = canvas.clientWidth / canvas.clientHeight;
    camera.aspect = aspect;
    camera.updateProjectionMatrix();
    renderer.setSize(canvas.clientWidth, canvas.clientHeight);
    renderer.setPixelRatio(getRenderPixelRatio());
}

function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
}

// File handling
function setupFileHandling() {
    // Click to upload
    overlay.addEventListener('click', (e) => {
        if (!overlay.classList.contains('has-file')) {
            fileInput.click();
        }
    });

    // File input change
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });

    // Drag and drop
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        canvas.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    canvas.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            const file = files[0];
            if (file.name.toLowerCase().endsWith('.ifc')) {
                handleFile(file);
            } else {
                alert('Please select a valid IFC file');
            }
        }
    });

    // Reupload button click
    reuploadBtn.addEventListener('click', () => {
        // Remove current model
        if (currentModel) {
            scene.remove(currentModel);
            currentModel = null;
        }

        // Hide reupload button
        reuploadBtn.style.display = 'none';

        // Reset file input
        fileInput.value = '';

        // Show upload overlay again
        overlay.style.display = 'flex';
        overlay.classList.remove('has-file');
        placeholder.style.display = 'block';
        fileInfo.style.display = 'none';
        if (exampleIfcBtn) {
            exampleIfcBtn.style.display = 'block';
        }
    });
}

function setupExampleRegulation() {
    if (!regulationInput) {
        return;
    }

    function applyExample(text) {
        regulationInput.value = text;
        regulationInput.focus();
        regulationInput.dispatchEvent(new Event('input', { bubbles: true }));
    }

    if (exampleRegulationBtn1) {
        exampleRegulationBtn1.addEventListener('click', () => {
            applyExample(exampleRegulationText1);
        });
    }

    if (exampleRegulationBtn2) {
        exampleRegulationBtn2.addEventListener('click', () => {
            applyExample(exampleRegulationText2);
        });
    }
}

function setupExampleIfcModel() {
    if (!exampleIfcBtn || !fileInput) {
        return;
    }

    exampleIfcBtn.addEventListener('click', async (event) => {
        event.preventDefault();
        event.stopPropagation();

        const originalText = exampleIfcBtn.textContent;
        exampleIfcBtn.disabled = true;
        exampleIfcBtn.textContent = 'Loading example IFC...';

        try {
            const blob = await fetchExampleIfcFile();
            const file = new File([blob], exampleIfcFileName, {
                type: blob.type || 'application/octet-stream'
            });
            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(file);
            fileInput.files = dataTransfer.files;
            fileInput.dispatchEvent(new Event('change', { bubbles: true }));
        } catch (error) {
            console.error('Example IFC load error:', error);
            alert('Failed to load example IFC model. Please make sure the backend is running.');
        } finally {
            exampleIfcBtn.disabled = false;
            exampleIfcBtn.textContent = originalText;
        }
    });
}

function handleFile(file) {
    // Update file input
    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(file);
    fileInput.files = dataTransfer.files;

    // Update UI
    placeholder.style.display = 'none';
    fileInfo.style.display = 'block';
    overlay.classList.add('has-file');

    fileNameDisplay.textContent = file.name;
    const sizeInMB = (file.size / (1024 * 1024)).toFixed(2);
    fileSizeDisplay.textContent = `Size: ${sizeInMB} MB`;

    console.log('File selected:', file.name);

    // Load the IFC model
    loadIFCModel(file);
}

function loadIFCModel(file) {
    // Remove previous model if exists
    if (currentModel) {
        scene.remove(currentModel);
        currentModel = null;
    }

    // Hide file info overlay immediately when loading starts
    overlay.style.display = 'none';

    // Show loading indicator
    const loadingText = document.createElement('div');
    loadingText.id = 'model-loading';
    loadingText.style.cssText = 'position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: white; font-size: 18px; z-index: 1000; pointer-events: none;';
    loadingText.textContent = 'Loading 3D model...';
    document.querySelector('.left-panel').appendChild(loadingText);

    // Create a URL for the file
    const url = URL.createObjectURL(file);

    ifcLoader.load(
        url,
        (ifcModel) => {
            // Remove loading indicator
            const loadingElement = document.getElementById('model-loading');
            if (loadingElement) {
                loadingElement.remove();
            }

            // Add model to scene
            currentModel = ifcModel;
            scene.add(currentModel);

            // Log model information
            console.log('IFC model loaded:', ifcModel);
            console.log('Model children count:', ifcModel.children.length);

            // Count actual meshes
            let meshCount = 0;
            ifcModel.traverse((child) => {
                if (child.isMesh) {
                    meshCount++;
                    // Add default material if missing
                    if (!child.material) {
                        child.material = new THREE.MeshStandardMaterial({
                            color: 0xcccccc,
                            side: THREE.DoubleSide
                        });
                    } else if (child.material.color) {
                        // Check if material is too dark
                        const brightness = child.material.color.r + child.material.color.g + child.material.color.b;
                        if (brightness < 0.1) {
                            console.warn('Dark material detected, brightening:', child.material.color);
                            child.material.color.setHex(0x888888);
                        }
                    }

                    // Enable double-sided rendering
                    if (child.material) {
                        child.material.side = THREE.DoubleSide;
                    }

                    // Ensure geometry is valid
                    if (child.geometry) {
                        child.geometry.computeBoundingBox();
                        child.geometry.computeBoundingSphere();
                    }
                }
            });

            console.log('Total mesh count:', meshCount);

            // Check if model is actually empty
            if (meshCount === 0 && ifcModel.children.length === 0) {
                console.error('Model appears to be empty or failed to load properly');
                alert('Warning: The IFC model appears to have geometry issues. The model may not display correctly.\n\nThis can happen with complex IFC files. Try:\n1. Simplifying the IFC file\n2. Using a different IFC export setting\n3. Checking the file in another IFC viewer');
            }

            // Auto-fit camera to model
            fitCameraToModel(currentModel);

            // Show reupload button
            reuploadBtn.style.display = 'block';
            if (exampleIfcBtn) {
                exampleIfcBtn.style.display = 'none';
            }

            console.log('IFC model loaded successfully');
            URL.revokeObjectURL(url);
        },
        (progress) => {
            const percent = (progress.loaded / progress.total) * 100;
            console.log(`Loading progress: ${percent.toFixed(2)}%`);
            const loadingElement = document.getElementById('model-loading');
            if (loadingElement) {
                loadingElement.textContent = `Loading 3D model... ${percent.toFixed(0)}%`;
            }
        },
        (error) => {
            console.error('Error loading IFC model:', error);
            const loadingElement = document.getElementById('model-loading');
            if (loadingElement) {
                loadingElement.textContent = 'Error loading model';
                setTimeout(() => loadingElement.remove(), 3000);
            }
            URL.revokeObjectURL(url);
            alert('Failed to load IFC model. Please check the console for details.');
        }
    );
}

function fitCameraToModel(model) {
    // Calculate bounding box of the model
    const box = new THREE.Box3().setFromObject(model);
    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());

    console.log('Model bounding box:', {
        min: box.min,
        max: box.max,
        size: size,
        center: center
    });

    // Check for NaN values
    if (isNaN(size.x) || isNaN(size.y) || isNaN(size.z) ||
        isNaN(center.x) || isNaN(center.y) || isNaN(center.z)) {
        console.error('Bounding box contains NaN values - using default camera position');

        // Set default camera position
        camera.position.set(50, 50, 50);
        camera.lookAt(0, 0, 0);
        controls.target.set(0, 0, 0);
        controls.update();

        // Use very generous near/far planes
        camera.near = 0.1;
        camera.far = 10000;
        camera.updateProjectionMatrix();

        console.warn('Using fallback camera position due to invalid geometry');
        return;
    }

    // Check if bounding box is valid
    if (size.x === 0 || size.y === 0 || size.z === 0) {
        console.error('Invalid bounding box - model might be empty or too small');

        // Set default camera position
        camera.position.set(50, 50, 50);
        camera.lookAt(0, 0, 0);
        controls.target.set(0, 0, 0);
        controls.update();
        return;
    }

    // Calculate the maximum dimension
    const maxDim = Math.max(size.x, size.y, size.z);
    const fov = camera.fov * (Math.PI / 180);
    let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2));

    const padding = 0.5;
    // Add padding for a closer view
    cameraZ *= padding;

    // Position camera at an angle
    camera.position.set(
        center.x + cameraZ * 0.5,
        center.y + cameraZ * 0.5,
        center.z + cameraZ * 0.5
    );
    camera.lookAt(center);

    // Update controls target
    controls.target.copy(center);
    controls.update();

    // Update camera near/far planes based on model size with more generous limits
    camera.near = Math.max(0.1, maxDim / 1000);
    camera.far = maxDim * 1000;
    camera.updateProjectionMatrix();

    console.log('Camera fitted to model:', {
        center: center,
        size: size,
        maxDim: maxDim,
        cameraZ: cameraZ,
        cameraPosition: camera.position,
        near: camera.near,
        far: camera.far
    });
}

// WebSocket Manager for real-time updates
class ComplianceWebSocket {
    constructor(sessionId) {
        this.sessionId = sessionId;
        this.ws = null;
        this.onIterationStarted = null;
        this.onIterationCompleted = null;
        this.onSubgoalUpdate = null;
        this.onCompletion = null;
        this.onError = null;
    }

    connect() {
        return new Promise((resolve, reject) => {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/${this.sessionId}`;

            console.log('[WebSocket] Connecting to:', wsUrl);
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log('[WebSocket] Connected');
                resolve();
            };

            this.ws.onmessage = (event) => {
                const message = JSON.parse(event.data);
                this.handleMessage(message);
            };

            this.ws.onerror = (error) => {
                console.error('[WebSocket] Error:', error);
                reject(error);
            };

            this.ws.onclose = (event) => {
                console.log('[WebSocket] Disconnected');
                if (!event.wasClean && this.onError) {
                    this.onError({ error: 'Connection lost unexpectedly' });
                }
            };
        });
    }

    handleMessage(message) {
        console.log('[WebSocket] Received:', message.type);

        switch (message.type) {
            case 'connected':
                console.log('[WebSocket] Session confirmed:', message.session_id);
                break;
            case 'iteration_started':
                if (this.onIterationStarted) this.onIterationStarted(message);
                break;
            case 'iteration_completed':
                if (this.onIterationCompleted) this.onIterationCompleted(message);
                break;
            case 'subgoal_update':
                if (this.onSubgoalUpdate) this.onSubgoalUpdate(message);
                break;
            case 'completion':
                if (this.onCompletion) this.onCompletion(message);
                this.close();
                break;
            case 'error':
                if (this.onError) this.onError(message);
                this.close();
                break;
        }
    }

    close() {
        if (this.ws) {
            this.ws.close();
        }
    }
}

// UI Functions for real-time progress display
function initializeProgressUI() {
    const resultDiv = document.getElementById('result');
    resultDiv.innerHTML = `
        <div id="subgoal-progress-bar" class="subgoal-progress-bar" style="display: none;">
            <div class="progress-bar-container">
                <div class="progress-bar-fill" style="width: 0%"></div>
            </div>
            <div class="progress-bar-text">0/0 completed</div>
        </div>
        <div id="iteration-container" class="iteration-container"></div>
        <div id="final-report" class="final-report" style="display: none;"></div>
    `;
    resultDiv.className = 'result show';
    resultDiv.style.display = 'block';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatActionResult(result) {
    const str = JSON.stringify(result, null, 2);
    if (str.length > 500) {
        return str.substring(0, 500) + '\n... (truncated)';
    }
    return str;
}

function updateProgressIndicator(activeSubgoalId) {
    // Progress indicator removed - no-op function
}

function generateIterationSummary(action, actionInput) {
    // Use tool name directly for execute_tool, otherwise use action name
    if (action.toLowerCase().includes('execute') && actionInput?.tool_name) {
        return actionInput.tool_name.replace(/_/g, ' ');
    }
    return action.replace(/_/g, ' ');
}

function summarizeInput(actionInput) {
    // Summarize input parameters
    if (!actionInput || typeof actionInput !== 'object') {
        return 'No parameters';
    }

    const entries = Object.entries(actionInput);
    if (entries.length === 0) {
        return 'No parameters';
    }

    const summary = [];
    entries.slice(0, 3).forEach(([key, value]) => {
        if (typeof value === 'string' && value.length > 50) {
            // Don't truncate task_description - show it in full
            if (key === 'task_description') {
                summary.push(`${key}: ${value}`);
            } else {
                summary.push(`${key}: ${value.substring(0, 50)}...`);
            }
        } else if (Array.isArray(value)) {
            summary.push(`${key}: ${value.length} item(s)`);
        } else if (typeof value === 'object' && value !== null) {
            summary.push(`${key}: [object]`);
        } else {
            summary.push(`${key}: ${value}`);
        }
    });

    if (entries.length > 3) {
        summary.push(`... and ${entries.length - 3} more`);
    }

    return summary.join(', ');
}

function formatFriendlyOutput(actionResult, action, actionInput) {
    // Generate human-friendly output based on action type
    if (!actionResult) return 'No result';

    let html = '';
    const actionName = action.toLowerCase();

    // Handle errors
    if (actionResult.error) {
        html += `<div class="output-item error">Error: ${escapeHtml(actionResult.error)}</div>`;
        return html;
    }

    if (actionResult.success === false) {
        const actionLabel = actionName.replace(/_/g, ' ');
        html += `<div class="output-item error">Failed to ${escapeHtml(actionLabel)}</div>`;
        return html;
    }

    // Generate action-specific descriptions
    if (actionName.includes('select') && actionName.includes('tool')) {
        // Tool selection
        // Try different possible structures
        let toolName = null;

        if (actionResult.result?.ifc_tool_name) {
            toolName = actionResult.result.ifc_tool_name;
        } else if (actionResult.result?.tool_name) {
            toolName = actionResult.result.tool_name;
        } else if (actionResult.ifc_tool_name) {
            toolName = actionResult.ifc_tool_name;
        } else if (actionResult.tool_name) {
            toolName = actionResult.tool_name;
        } else if (typeof actionResult.result === 'string') {
            toolName = actionResult.result;
        }

        if (toolName) {
            html += `<div class="output-item">Successfully selected tool: ${escapeHtml(toolName)}</div>`;
        } else {
            html += `<div class="output-item">Successfully selected tool</div>`;
        }
    } else if (actionName.includes('create') && actionName.includes('tool')) {
        // Tool creation
        let toolName = null;

        if (actionResult.result?.ifc_tool_name) {
            toolName = actionResult.result.ifc_tool_name;
        } else if (actionResult.result?.tool_name) {
            toolName = actionResult.result.tool_name;
        } else if (actionResult.ifc_tool_name) {
            toolName = actionResult.ifc_tool_name;
        } else if (actionResult.tool_name) {
            toolName = actionResult.tool_name;
        } else if (actionInput?.tool_name) {
            toolName = actionInput.tool_name;
        }

        if (toolName) {
            html += `<div class="output-item">Successfully created tool: ${escapeHtml(toolName)}</div>`;
        } else {
            html += `<div class="output-item">Successfully created tool</div>`;
        }

        if (actionResult.tool_path || actionResult.result?.tool_path) {
            const path = actionResult.tool_path || actionResult.result.tool_path;
            html += `<div class="output-item-detail">Saved to: ${escapeHtml(path)}</div>`;
        }
    } else if (actionName.includes('store') && actionName.includes('tool')) {
        // Store tool
        let toolName = null;

        if (actionResult.result?.ifc_tool_name) {
            toolName = actionResult.result.ifc_tool_name;
        } else if (actionResult.ifc_tool_name) {
            toolName = actionResult.ifc_tool_name;
        } else if (actionInput?.tool_name) {
            toolName = actionInput.tool_name;
        }

        if (toolName) {
            html += `<div class="output-item">Successfully stored tool: ${escapeHtml(toolName)}</div>`;
        } else {
            html += `<div class="output-item">Successfully stored tool in registry</div>`;
        }

        if (actionResult.result?.tool_path || actionResult.tool_path) {
            const path = actionResult.result?.tool_path || actionResult.tool_path;
            html += `<div class="output-item-detail">Path: ${escapeHtml(path)}</div>`;
        }
    } else if (actionName.includes('fix') && actionName.includes('tool')) {
        // Fix tool
        let toolName = null;

        if (actionResult.result?.ifc_tool_name) {
            toolName = actionResult.result.ifc_tool_name;
        } else if (actionResult.ifc_tool_name) {
            toolName = actionResult.ifc_tool_name;
        } else if (actionInput?.tool_name) {
            toolName = actionInput.tool_name;
        }

        if (toolName) {
            html += `<div class="output-item">Successfully fixed tool: ${escapeHtml(toolName)}</div>`;
        } else {
            html += `<div class="output-item">Successfully fixed tool</div>`;
        }

        // Show what was fixed
        if (actionResult.result?.fixed_issues || actionResult.fixed_issues) {
            const issues = actionResult.result?.fixed_issues || actionResult.fixed_issues;
            if (Array.isArray(issues) && issues.length > 0) {
                html += `<div class="output-item">Fixed ${issues.length} issue(s)</div>`;
                issues.slice(0, 3).forEach((issue, idx) => {
                    html += `<div class="output-item-detail">${idx + 1}. ${escapeHtml(issue)}</div>`;
                });
                if (issues.length > 3) {
                    html += `<div class="output-item-detail">... and ${issues.length - 3} more</div>`;
                }
            }
        }

        if (actionResult.result?.tool_path || actionResult.tool_path) {
            const path = actionResult.result?.tool_path || actionResult.tool_path;
            html += `<div class="output-item-detail">Updated: ${escapeHtml(path)}</div>`;
        }
    } else if (actionName.includes('execute') || actionName.includes('run')) {
        // Tool execution
        let toolName = null;

        // Try to get tool name from various sources
        if (actionResult.result?.ifc_tool_name) {
            toolName = actionResult.result.ifc_tool_name;
        } else if (actionResult.ifc_tool_name) {
            toolName = actionResult.ifc_tool_name;
        } else if (actionInput?.tool_name) {
            toolName = actionInput.tool_name;
        }

        if (!toolName) {
            toolName = 'tool';
        }

        // Try to find the actual result data
        let actualResult = null;
        if (actionResult.result?.result) {
            actualResult = actionResult.result.result;
        } else if (Array.isArray(actionResult.result)) {
            actualResult = actionResult.result;
        } else if (actionResult.data) {
            actualResult = actionResult.data;
        }

        if (Array.isArray(actualResult)) {
            // Try to extract element type from result
            let elementType = 'element';
            if (actualResult.length > 0 && actualResult[0].type) {
                elementType = actualResult[0].type;
            } else if (toolName.includes('door')) {
                elementType = 'IfcDoor';
            } else if (toolName.includes('stair')) {
                elementType = 'IfcStair';
            } else if (toolName.includes('window')) {
                elementType = 'IfcWindow';
            }

            html += `<div class="output-item">Successfully executed tool: ${escapeHtml(toolName.replace(/_/g, ' '))}</div>`;
            html += `<div class="output-item">Retrieved ${actualResult.length} ${elementType} element(s)</div>`;
        } else {
            html += `<div class="output-item">Successfully executed tool: ${escapeHtml(toolName.replace(/_/g, ' '))}</div>`;
            if (actionResult.result?.message) {
                html += `<div class="output-item">${escapeHtml(actionResult.result.message)}</div>`;
            }
        }
    } else if (actionName.includes('extract') || actionName.includes('get')) {
        // Extract/Get operations
        let actualResult = null;

        // Try different possible structures
        if (actionResult.result?.result) {
            actualResult = actionResult.result.result;
        } else if (Array.isArray(actionResult.result)) {
            actualResult = actionResult.result;
        } else if (actionResult.data) {
            actualResult = actionResult.data;
        }

        // Determine element type from action name or result
        let elementType = 'element';
        if (actionName.includes('door')) elementType = 'IfcDoor';
        else if (actionName.includes('stair')) elementType = 'IfcStair';
        else if (actionName.includes('window')) elementType = 'IfcWindow';
        else if (actionName.includes('wall')) elementType = 'IfcWall';
        else if (actionName.includes('space')) elementType = 'IfcSpace';
        else if (Array.isArray(actualResult) && actualResult.length > 0 && actualResult[0].type) {
            elementType = actualResult[0].type;
        }

        if (Array.isArray(actualResult)) {
            html += `<div class="output-item">Retrieved ${actualResult.length} ${elementType} element(s)</div>`;
        } else if (actualResult !== undefined) {
            html += `<div class="output-item">Retrieved ${elementType} data</div>`;
        }
    } else if (actionName.includes('interpret') || actionName.includes('regulation')) {
        // Regulation interpretation
        html += `<div class="output-item">Successfully interpreted building code requirements</div>`;
        if (actionResult.requirements) {
            const reqCount = Array.isArray(actionResult.requirements) ? actionResult.requirements.length : Object.keys(actionResult.requirements).length;
            html += `<div class="output-item">Identified ${reqCount} requirement(s)</div>`;
        }
    } else if ((actionName.includes('generate') && actionName.includes('subgoal')) ||
               (actionName.includes('review') && actionName.includes('subgoal')) ||
               (actionName.includes('update') && actionName.includes('subgoal'))) {
        // Subgoal generation or review/update
        // Try to extract from actionResult first, then fall back to window.currentSubgoals
        let subgoals = null;

        // Try different possible structures in actionResult
        if (Array.isArray(actionResult.result)) {
            subgoals = actionResult.result;
        } else if (actionResult.result?.subgoals && Array.isArray(actionResult.result.subgoals)) {
            subgoals = actionResult.result.subgoals;
        } else if (Array.isArray(actionResult.subgoals)) {
            subgoals = actionResult.subgoals;
        } else if (window.currentSubgoals && window.currentSubgoals.length > 0) {
            // Fallback to window.currentSubgoals
            subgoals = window.currentSubgoals;
        }

        if (!subgoals) {
            subgoals = [];
        }

        const count = subgoals.length;

        if (actionName.includes('generate')) {
            html += `<div class="output-item">Successfully generated ${count} subgoal(s)</div>`;
        } else if (actionName.includes('review') || actionName.includes('update')) {
            html += `<div class="output-item">Successfully reviewed and updated ${count} subgoal(s)</div>`;
        }

        // Show all subgoals with status
        if (subgoals.length > 0) {
            html += '<div style="margin-top: 8px;">';
            subgoals.forEach(subgoal => {
                const statusClass = subgoal.status === 'completed' ? 'completed' :
                                  subgoal.status === 'in_progress' ? 'in-progress' : 'pending';
                const statusText = subgoal.status === 'completed' ? 'Completed' :
                                 subgoal.status === 'in_progress' ? 'In Progress' : 'Pending';

                html += `
                    <div class="subgoal-item-inline ${statusClass}">
                        <span class="subgoal-id-inline">${subgoal.id}.</span>
                        <span class="subgoal-desc-inline">${escapeHtml(subgoal.description)}</span>
                        <span class="subgoal-status-inline">${statusText}</span>
                    </div>
                `;
            });
            html += '</div>';
        }
    } else if (actionName.includes('evaluate') || actionName.includes('compliance')) {
        // Compliance evaluation
        html += `<div class="output-item">Successfully evaluated compliance and generated report</div>`;
        if (actionResult.overall_status) {
            html += `<div class="output-item">Overall status: ${escapeHtml(actionResult.overall_status)}</div>`;
        }
    } else {
        // Generic fallback
        if (actionResult.result !== undefined) {
            const result = actionResult.result;
            if (Array.isArray(result)) {
                html += `<div class="output-item">Retrieved ${result.length} item(s)</div>`;
            } else if (typeof result === 'object' && result !== null) {
                html += `<div class="output-item">Operation completed with result data</div>`;
            } else {
                html += `<div class="output-item">Result: ${escapeHtml(String(result))}</div>`;
            }
        } else if (actionResult.message) {
            html += `<div class="output-item">${escapeHtml(actionResult.message)}</div>`;
        } else {
            html += `<div class="output-item">Operation completed successfully</div>`;
        }
    }

    return html;
}

function handleIterationStarted(message) {
    const container = document.getElementById('iteration-container');

    if (message.active_subgoal_id) {
        updateProgressIndicator(message.active_subgoal_id);
    }

    const summary = generateIterationSummary(message.action, message.action_input);
    const inputSummary = summarizeInput(message.action_input);

    const card = document.createElement('div');
    card.className = 'iteration-card';
    card.id = `iteration-${message.iteration}`;

    // Store action and input for later use
    card.dataset.action = message.action;
    card.dataset.actionInput = JSON.stringify(message.action_input);

    card.innerHTML = `
        <div class="iteration-header">
            <span class="iteration-number">Iteration ${message.iteration}</span>
            <span class="iteration-summary-inline">${escapeHtml(summary)}</span>
        </div>

        <div class="thought-section">
            <strong class="section-label">Thought:</strong>
            <div style="margin-top: 5px;">${escapeHtml(message.thought)}</div>
        </div>

        <div class="input-summary-section">
            <strong class="section-label">Input:</strong>
            <div class="input-summary-content">${escapeHtml(inputSummary)}</div>
        </div>

        <div class="action-output-section">
            <strong class="section-label">Output:</strong>
            <div class="loading-output">Executing...</div>
        </div>

        <button class="toggle-details-btn" onclick="toggleTechnicalDetails(${message.iteration})">
            Show details
        </button>

        <div class="technical-details" style="display: none;">
            <div class="detail-section">
                <strong class="section-label">Action:</strong>
                <pre>${escapeHtml(message.action)}</pre>
            </div>

            <div class="detail-section">
                <strong class="section-label">Input (Full):</strong>
                <pre>${escapeHtml(JSON.stringify(message.action_input, null, 2))}</pre>
            </div>

            <div class="detail-section" id="output-detail-${message.iteration}">
                <strong class="section-label">Output (Full):</strong>
                <pre>Executing...</pre>
            </div>
        </div>
    `;

    container.appendChild(card);
    card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function handleIterationCompleted(message) {
    const card = document.getElementById(`iteration-${message.iteration}`);
    if (!card) {
        console.error('[Client] Could not find iteration card:', message.iteration);
        return;
    }

    const outputSection = card.querySelector('.action-output-section');
    const success = message.action_result?.success;
    const statusText = success ? 'Success' : 'Failed';
    const statusClass = success ? 'status-success' : 'status-failed';

    // Update header with status badge
    const header = card.querySelector('.iteration-header');
    const existingStatus = header.querySelector('.status-badge');
    if (!existingStatus) {
        const statusSpan = document.createElement('span');
        statusSpan.className = `status-badge ${statusClass}`;
        statusSpan.textContent = statusText;
        header.appendChild(statusSpan);
    }

    // Get action and actionInput from card dataset
    const action = card.dataset.action || '';
    const actionInput = card.dataset.actionInput ? JSON.parse(card.dataset.actionInput) : {};

    // Check if this is a subgoal-related action and extract subgoals from result
    const actionName = action.toLowerCase();
    if ((actionName.includes('generate') && actionName.includes('subgoal')) ||
        (actionName.includes('review') && actionName.includes('subgoal')) ||
        (actionName.includes('update') && actionName.includes('subgoal'))) {

        // Extract subgoals from actionResult and update window.currentSubgoals
        let subgoals = null;
        if (Array.isArray(message.action_result.result)) {
            subgoals = message.action_result.result;
        } else if (message.action_result.result?.subgoals && Array.isArray(message.action_result.result.subgoals)) {
            subgoals = message.action_result.result.subgoals;
        } else if (Array.isArray(message.action_result.subgoals)) {
            subgoals = message.action_result.subgoals;
        }

        if (subgoals && subgoals.length > 0) {
            window.currentSubgoals = subgoals;
            console.log('[Client] Updated currentSubgoals from action result:', subgoals.length);

            // Also update progress bar with the latest subgoals
            updateSubgoalProgressBar(subgoals);
        }
    }

    // Generate friendly output
    const friendlyOutput = formatFriendlyOutput(message.action_result, action, actionInput);
    const fullOutputJSON = JSON.stringify(message.action_result, null, 2);

    // Update main output section with friendly format
    outputSection.innerHTML = `
        <strong class="section-label">Output:</strong>
        <div class="friendly-output">
            ${friendlyOutput}
        </div>
    `;

    // Update technical details with full JSON
    const outputDetail = card.querySelector(`#output-detail-${message.iteration}`);
    if (outputDetail) {
        outputDetail.innerHTML = `
            <strong class="section-label">Output (Full):</strong>
            <pre>${escapeHtml(fullOutputJSON)}</pre>
        `;
    }

    card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function handleSubgoalUpdate(message) {
    console.log('[Client] Subgoals updated:', message.subgoals.length);
    window.currentSubgoals = message.subgoals;

    // Only update progress bar, don't create separate card
    // Subgoals will be displayed in the generate_subgoals or review_subgoals action output
    updateSubgoalProgressBar(message.subgoals);
}

function toggleTechnicalDetails(iteration) {
    const card = document.getElementById(`iteration-${iteration}`);
    const technicalDetails = card.querySelector('.technical-details');
    const toggleBtn = card.querySelector('.toggle-details-btn');

    if (technicalDetails.style.display === 'none') {
        technicalDetails.style.display = 'block';
        toggleBtn.textContent = 'Hide details';
    } else {
        technicalDetails.style.display = 'none';
        toggleBtn.textContent = 'Show details';
    }
}

function updateSubgoalProgressBar(subgoals) {
    const progressBar = document.getElementById('subgoal-progress-bar');
    const progressFill = progressBar.querySelector('.progress-bar-fill');
    const progressText = progressBar.querySelector('.progress-bar-text');

    // Show progress bar on first subgoal update
    if (progressBar.style.display === 'none') {
        progressBar.style.display = 'flex';
    }

    // Calculate progress
    const total = subgoals.length;
    const completed = subgoals.filter(s => s.status === 'completed').length;
    const percentage = total > 0 ? (completed / total) * 100 : 0;

    // Update UI
    progressFill.style.width = `${percentage}%`;
    progressText.textContent = `${completed}/${total} completed`;
}

function handleCompletion(message) {
    console.log('[Client] Check completed:', message.status);

    const submitBtn = document.getElementById('submitBtn');
    submitBtn.disabled = false;

    // Update progress bar to 100%
    const progressBar = document.getElementById('subgoal-progress-bar');
    if (progressBar && progressBar.style.display !== 'none') {
        const progressFill = progressBar.querySelector('.progress-bar-fill');
        const progressText = progressBar.querySelector('.progress-bar-text');
        if (window.currentSubgoals) {
            const total = window.currentSubgoals.length;
            progressFill.style.width = '100%';
            progressText.textContent = `${total}/${total} completed`;
        }
    }

    if (message.compliance_result) {
        displayFinalReport(message.compliance_result);
    } else if (message.error) {
        handleError({ error: message.error });
    }
}

function displayFinalReport(result) {
    const reportDiv = document.getElementById('final-report');

    const overallStatus = result.overall_status;
    let statusText = 'UNKNOWN';
    let statusColor = '#666';

    if (overallStatus === 'compliant') {
        statusText = 'COMPLIANT';
        statusColor = '#28a745';
    } else if (overallStatus === 'non_compliant') {
        statusText = 'NON-COMPLIANT';
        statusColor = '#dc3545';
    } else if (overallStatus === 'not_applicable') {
        statusText = 'NOT APPLICABLE';
        statusColor = '#6c757d';
    }

    let reportHtml = `
        <h3>Final Compliance Report</h3>
        <div class="report-card">
            <h4 style="color: ${statusColor}">${statusText}</h4>
            <p><strong>Total Components:</strong> ${
                (result.compliant_components?.length || 0) +
                (result.non_compliant_components?.length || 0) +
                (result.not_applicable_components?.length || 0)
            }</p>
            <p style="color: #7fc29b">Compliant: ${result.compliant_components?.length || 0}</p>
            <p style="color: #c9736c">Non-Compliant: ${result.non_compliant_components?.length || 0}</p>
            <p style="color: #8b9299">Not Applicable: ${result.not_applicable_components?.length || 0}</p>
        </div>
    `;

    if (result.non_compliant_components?.length > 0) {
        reportHtml += `<div class="report-card">
            <h4 style="color: #c9736c">Non-Compliant Components</h4>`;
        result.non_compliant_components.forEach(comp => {
            reportHtml += `
                <div style="border-left: 4px solid #c9736c; padding: 10px; margin: 10px 0; background-color: #fdf6f5;">
                    <strong>${comp.component_type}</strong>
                    <span style="color: #666; font-size: 0.85em;">(ID: ${comp.component_id})</span>
                    <br><small style="color: #c9736c"><strong>Violation:</strong> ${comp.violation_reason || 'No details'}</small>
                    ${comp.suggested_fix ? `<br><small style="color: #6ba3d4"><strong>Fix:</strong> ${comp.suggested_fix}</small>` : ''}
                    <br><small><strong>Data:</strong> ${JSON.stringify(comp.data_used)}</small>
                </div>
            `;
        });
        reportHtml += `</div>`;
    }

    reportDiv.innerHTML = reportHtml;
    reportDiv.style.display = 'block';
    reportDiv.scrollIntoView({ behavior: 'smooth' });
}

function handleError(message) {
    const result = document.getElementById('result');
    result.className = 'result show error';
    result.innerHTML = `
        <h3>Check Failed</h3>
        <p style="color: #c9736c">${escapeHtml(message.error)}</p>
        <button onclick="location.reload()">Retry</button>
    `;

    document.getElementById('submitBtn').disabled = false;
}

// Form submission with WebSocket real-time updates
function setupFormSubmission() {
    document.getElementById('checkForm').addEventListener('submit', async function(e) {
        e.preventDefault();

        const submitBtn = document.getElementById('submitBtn');
        const loading = document.getElementById('loading');

        submitBtn.disabled = true;
        loading.style.display = 'block';

        try {
            const formData = new FormData(this);

            // Step 1: Start compliance check and get session ID
            const response = await fetch('/check/start', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Failed to start check: ${response.statusText}`);
            }

            const { session_id } = await response.json();
            console.log('[Client] Session started:', session_id);

            // Step 2: Initialize progress UI
            initializeProgressUI();
            loading.style.display = 'none';

            // Step 3: Connect to WebSocket for real-time updates
            const ws = new ComplianceWebSocket(session_id);

            ws.onIterationStarted = handleIterationStarted;
            ws.onIterationCompleted = handleIterationCompleted;
            ws.onSubgoalUpdate = handleSubgoalUpdate;
            ws.onCompletion = handleCompletion;
            ws.onError = handleError;

            await ws.connect();
            console.log('[Client] WebSocket connected, waiting for updates...');

        } catch (error) {
            console.error('[Client] Error:', error);
            const result = document.getElementById('result');
            result.className = 'result show error';
            result.innerHTML = `<h3>Check Failed</h3><p>Error: ${error.message}</p>`;
            submitBtn.disabled = false;
            loading.style.display = 'none';
        }
    });
}

// Initialize everything
initViewer();
setupFileHandling();
setupExampleRegulation();
setupExampleIfcModel();
setupFormSubmission();
