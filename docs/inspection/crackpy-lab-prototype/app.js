(function () {
  const fallbackData = {
    experiments: [],
    methods: [],
    provenance: [],
    warnings: ["No CrackPy fixture data was loaded."],
    visualizationConfig: {}
  };

  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => Array.from(document.querySelectorAll(selector));

  function firstMetric(frame, label, preferredSource) {
    const metrics = frame.metrics || [];
    return metrics.find((metric) => metric.label === label && metric.methodSource === preferredSource)
      || metrics.find((metric) => metric.label === label)
      || { value: null, unit: "", methodSource: "not run" };
  }

  function parseFrameNumber(frame) {
    const match = String(frame.label || frame.id || "").match(/(\d+)/);
    return match ? Number(match[1]) : 0;
  }

  function metricValue(frame, label, preferredSource) {
    const metric = firstMetric(frame, label, preferredSource);
    return metric && metric.value != null ? Number(metric.value) : null;
  }

  function normalizeData(raw) {
    if (raw.experiments) {
      return raw;
    }

    const presets = raw.experimentPresets || [];
    const resultFrames = raw.resultFrames || [];
    const methods = (raw.analysisMethods || []).map((method) => ({
      label: method.label,
      source: method.methodSource,
      value: method.outputLabels.join(", ")
    }));

    const experiments = presets.map((preset) => {
      const frames = resultFrames
        .filter((frame) => frame.experimentPresetId === preset.id)
        .map((frame) => {
          const frameNumber = parseFrameNumber(frame);
          const kiMetric = firstMetric(frame, "K_I", "Williams fit");
          const kiiMetric = firstMetric(frame, "K_II", "Williams fit");
          const jMetric = firstMetric(frame, "J", "J-integral");
          const residual = frame.residual
            ?? metricValue(frame, "Error_xy", "Williams fit")
            ?? metricValue(frame, "Error_z", "Williams fit")
            ?? metricValue(frame, "Error", "CJP model");
          return {
            sourceId: frame.id,
            frame: frameNumber,
            cycles: frame.cycles ?? preset.loading.cycle,
            load: frame.load ?? preset.loading.load,
            displacement: frame.displacement ?? preset.loading.displacement,
            a: frame.correctedCrackTipEstimate.x,
            tipY: frame.correctedCrackTipEstimate.y,
            angle: frame.correctedCrackTipEstimate.angle,
            dx: frame.correctionDelta.dx,
            dy: frame.correctionDelta.dy,
            ki: kiMetric.value,
            kii: kiiMetric.value,
            kiSource: kiMetric.methodSource || "Williams fit",
            kiiSource: kiiMetric.methodSource || "Williams fit",
            j: jMetric.value,
            jUnit: jMetric.unit || "N/mm",
            residual,
            status: frame.warningIds && frame.warningIds.some((id) => id.includes("dropout") || id.includes("rotation")) ? "review" : "ok",
            raw: frame
          };
        });

      return {
        id: preset.id,
        name: preset.label,
        meta: `${frames.length} actual frames, ${preset.specimen.geometry}, ${preset.specimen.material}`,
        nodemaps: Array.from(new Set(frames.map((frame) => frame.raw.imageName))),
        materials: [`${preset.specimen.material}${preset.specimen.thickness ? `, thickness=${preset.specimen.thickness} mm` : ""}${preset.specimen.width ? `, W=${preset.specimen.width} mm` : ""}`],
        defaultFrame: frames[0] ? frames[0].frame : 0,
        frames
      };
    });

    return {
      experiments,
      methods,
      provenance: (raw.provenanceSteps || []).map((step) => ({ title: step.label, detail: step.detail })),
      graphNodeTypes: raw.graphNodeTypes || [],
      graphEdges: raw.graphEdges || [],
      graphNodeDetails: raw.graphNodeDetails || {},
      graphArtifacts: raw.graphArtifacts || [],
      visualizationConfig: raw.visualizationConfig || {},
      actualDataSources: (raw.actualDataSources || []).filter(Boolean),
      actualGraphSummary: raw.actualGraphSummary || {},
      dataPolicy: raw.dataPolicy || "",
      warnings: raw.warnings || fallbackData.warnings,
      warningMap: new Map((raw.warnings || []).map((warning) => [warning.id, warning]))
    };
  }

  const data = normalizeData(window.CrackPyPrototypeData || fallbackData);
  if (!data.experiments.length) {
    throw new Error("CrackPy Lab prototype requires generated actual fixture data.");
  }

  const featureDefinitions = [
    ["setup-panel", "Setup panel"],
    ["field-panel", "Field panel"],
    ["result-panel", "Result panel"],
    ["frame-table", "Frame table"],
    ["provenance-panel", "Provenance panel"],
    ["config-lenses", "Setup lenses"],
    ["field-image", "Nodemap base image"],
    ["mesh-overlay", "Nodemap mesh"],
    ["line-integral-paths", "Line integral paths"],
    ["annulus-overlay", "Williams annulus"],
    ["detection-window", "Crack-tip detection window"],
    ["crack-tip-markers", "Crack-tip markers"],
    ["crack-path", "Crack path"],
    ["crack-tip-axis", "Crack-tip axis"],
    ["metric-cards", "Metric cards"],
    ["method-evidence", "Method evidence"],
    ["method-stack", "Method stack"],
    ["scientific-warnings", "Scientific warnings"],
    ["graph-artifact-controls", "Graph artifact controls"],
    ["analysis-graph", "Analysis graph"],
    ["source-evidence", "Source evidence"],
    ["node-surface-matrix", "Node surface matrix"],
    ["provenance-flow", "Provenance flow"],
    ["graph-node-chips", "Graph node chips"],
    ["node-inspector", "Node inspector"],
    ["provenance-snippet", "Provenance JSON"]
  ].map(([key, label]) => ({ key, label, selector: `[data-feature="${key}"]` }));

  const featureFlags = Object.fromEntries(featureDefinitions.map((feature) => [feature.key, true]));
  const state = {
    experimentId: data.experiments[0].id,
    frame: data.experiments[0].defaultFrame,
    correction: "actual",
    overlay: "eps_eqv",
    fieldColoring: data.visualizationConfig?.nodemapBaseLayer?.defaultColormap || "turbo",
    fieldScalePreset: "auto",
    fieldSigma: 2,
    fieldVmin: null,
    fieldVmax: null,
    fieldZoom: 1,
    setupOverlayMode: "combined",
    showLinePaths: true,
    showAnnulus: true,
    showDetectionWindow: true,
    methodEvidenceMode: "williamsTerms",
    graphArtifactId: (data.graphArtifacts && data.graphArtifacts[0]?.id) || "legacy-graph",
    selectedGraphNode: "InputRecord",
    running: false,
    featureFlags
  };

  const defaultPathCount = data.visualizationConfig?.lineIntegralDefaults?.number_of_paths || 9;
  const defaultWilliams = data.visualizationConfig?.williamsDefaults || {};

  const els = {
    experimentSelect: $("#experimentSelect"),
    nodemapSelect: $("#nodemapSelect"),
    materialSelect: $("#materialSelect"),
    sideSelect: $("#sideSelect"),
    sideRunName: $("#sideRunName"),
    sideRunMeta: $("#sideRunMeta"),
    sideProgress: $("#sideProgress"),
    runBadge: $("#runBadge"),
    runMessage: $("#runMessage"),
    startRunButton: $("#startRunButton"),
    resetButton: $("#resetButton"),
    overlayReadout: $("#overlayReadout"),
    fieldSvg: $("#fieldSvg"),
    fieldCanvas: $("#fieldCanvas"),
    tipReadout: $("#tipReadout"),
    deltaReadout: $("#deltaReadout"),
    fieldScaleReadout: $("#fieldScaleReadout"),
    setupGeometryReadout: $("#setupGeometryReadout"),
    activeFrameLabel: $("#activeFrameLabel"),
    metricGrid: $("#metricGrid"),
    methodEvidenceMode: $("#methodEvidenceMode"),
    methodEvidenceTitle: $("#methodEvidenceTitle"),
    methodEvidenceTable: $("#methodEvidenceTable"),
    methodStack: $("#methodStack"),
    warningList: $("#warningList"),
    frameRows: $("#frameRows"),
    configLenses: $("#configLenses"),
    graphArtifactSelect: $("#graphArtifactSelect"),
    graphArtifactSummary: $("#graphArtifactSummary"),
    analysisGraph: $("#analysisGraph"),
    sourceEvidence: $("#sourceEvidence"),
    nodeSurfaceMatrix: $("#nodeSurfaceMatrix"),
    provenanceFlow: $("#provenanceFlow"),
    graphNodeChips: $("#graphNodeChips"),
    nodeInspectorTitle: $("#nodeInspectorTitle"),
    nodeInspectorRole: $("#nodeInspectorRole"),
    nodeInspectorFields: $("#nodeInspectorFields"),
    provenanceBadge: $("#provenanceBadge"),
    provenanceSnippet: $("#provenanceSnippet"),
    qualityBadge: $("#qualityBadge"),
    setupGeometryLayer: $("#setupGeometryLayer"),
    exportButton: $("#exportButton"),
    showLinePaths: $("#showLinePaths"),
    showAnnulus: $("#showAnnulus"),
    showDetectionWindow: $("#showDetectionWindow"),
    setupOverlayMode: $("#setupOverlayMode"),
    fieldColoring: $("#fieldColoring"),
    fieldScalePreset: $("#fieldScalePreset"),
    fieldSigma: $("#fieldSigma"),
    fieldVmin: $("#fieldVmin"),
    fieldVmax: $("#fieldVmax"),
    fieldZoom: $("#fieldZoom"),
    debugFeatureMatrix: $("#debugFeatureMatrix"),
    runDebugAssertions: $("#runDebugAssertions"),
    resetFeatureFlags: $("#resetFeatureFlags"),
    debugAssertionStatus: $("#debugAssertionStatus"),
    debugState: $("#debugState")
  };

  function activeExperiment() {
    return data.experiments.find((experiment) => experiment.id === state.experimentId) || data.experiments[0];
  }

  function activeFrame() {
    const experiment = activeExperiment();
    return experiment.frames.find((frame) => frame.frame === state.frame) || experiment.frames[0];
  }

  function allFrames() {
    return data.experiments.flatMap((experiment) => (
      experiment.frames.map((frame) => ({ experiment, frame }))
    ));
  }

  function graphArtifacts() {
    if (Array.isArray(data.graphArtifacts) && data.graphArtifacts.length) {
      return data.graphArtifacts;
    }
    return [{
      id: "legacy-graph",
      label: "Williams proof export",
      method: "Williams fit",
      path: data.actualGraphSummary?.path || "",
      nodeCount: data.actualGraphSummary?.nodeCount || (data.graphNodeTypes || []).length,
      edgeCount: data.actualGraphSummary?.edgeCount || (data.graphEdges || []).length,
      nodeTypes: data.graphNodeTypes || [],
      edges: data.graphEdges || [],
      nodeDetails: data.graphNodeDetails || {},
      summary: data.actualGraphSummary || {}
    }];
  }

  function activeGraphArtifact() {
    const artifacts = graphArtifacts();
    return artifacts.find((artifact) => artifact.id === state.graphArtifactId) || artifacts[0];
  }

  function activeGraphNodeTypes() {
    return activeGraphArtifact()?.nodeTypes || [];
  }

  function activeGraphNodeDetails() {
    return activeGraphArtifact()?.nodeDetails || {};
  }

  function activeGraphSummary() {
    return activeGraphArtifact()?.summary || data.actualGraphSummary || {};
  }

  function formatNumber(value, digits) {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric.toFixed(digits) : "n/a";
  }

  function populateSelect(select, values, selectedValue) {
    select.innerHTML = values.map((value) => {
      const selected = value === selectedValue ? " selected" : "";
      return `<option value="${value}"${selected}>${value}</option>`;
    }).join("");
  }

  function renderExperimentControls() {
    els.experimentSelect.innerHTML = data.experiments.map((experiment) => {
      const selected = experiment.id === state.experimentId ? " selected" : "";
      return `<option value="${experiment.id}"${selected}>${experiment.name}</option>`;
    }).join("");

    const experiment = activeExperiment();
    const frame = activeFrame();
    populateSelect(els.nodemapSelect, experiment.nodemaps, frame.raw?.imageName || experiment.nodemaps[0]);
    populateSelect(els.materialSelect, experiment.materials, experiment.materials[0]);
    els.sideSelect.value = experiment.id.includes("-left") ? "left" : "right";
    els.sideRunName.textContent = experiment.name;
    els.sideRunMeta.textContent = experiment.meta;
  }

  function applyFieldZoom() {
    const zoom = Math.max(1, Number(state.fieldZoom) || 1);
    const frame = activeFrame();
    const point = mapFieldPoint(frame.a, frame.tipY);
    const originX = Number.isFinite(point.x) ? (point.x / 780) * 100 : 50;
    const originY = Number.isFinite(point.y) ? (point.y / 500) * 100 : 50;
    const transform = `scale(${zoom})`;
    [els.fieldSvg, els.fieldCanvas].forEach((element) => {
      element.style.transformOrigin = `${originX}% ${originY}%`;
      element.style.transform = transform;
    });
  }

  function fieldPlotBox() {
    const base = data.visualizationConfig?.nodemapBaseLayer || {};
    const xRange = base.xRange_mm || [0, 1];
    const yRange = base.yRange_mm || [0, 1];
    const imageBox = { x: 18, y: 20, width: 744, height: 452 };
    const dataAspect = (xRange[1] - xRange[0]) / (yRange[1] - yRange[0]);
    const boxAspect = imageBox.width / imageBox.height;
    let plotX = imageBox.x;
    let plotY = imageBox.y;
    let plotWidth = imageBox.width;
    let plotHeight = imageBox.height;

    if (dataAspect > boxAspect) {
      plotHeight = imageBox.width / dataAspect;
      plotY = imageBox.y + (imageBox.height - plotHeight) / 2;
    } else {
      plotWidth = imageBox.height * dataAspect;
      plotX = imageBox.x + (imageBox.width - plotWidth) / 2;
    }

    return { xRange, yRange, plotX, plotY, plotWidth, plotHeight };
  }

  function mapFieldPoint(x, y) {
    const box = fieldPlotBox();
    const px = box.plotX + ((Number(x) - box.xRange[0]) / (box.xRange[1] - box.xRange[0])) * box.plotWidth;
    const py = box.plotY + box.plotHeight - ((Number(y) - box.yRange[0]) / (box.yRange[1] - box.yRange[0])) * box.plotHeight;
    return { x: px, y: py };
  }

  function mmToScreen(mm) {
    const box = fieldPlotBox();
    const xScale = box.plotWidth / (box.xRange[1] - box.xRange[0]);
    const yScale = box.plotHeight / (box.yRange[1] - box.yRange[0]);
    return Number(mm) * Math.min(xScale, yScale);
  }

  function pointColumnIndex(column) {
    const columns = data.visualizationConfig?.nodemapBaseLayer?.pointData?.columns || [];
    return columns.indexOf(column);
  }

  function fieldRows() {
    return data.visualizationConfig?.nodemapBaseLayer?.pointData?.rows || [];
  }

  function colorStops(name) {
    const palettes = {
      turbo: [[48, 18, 59], [36, 94, 173], [31, 161, 135], [136, 204, 69], [251, 187, 56], [194, 51, 37]],
      viridis: [[68, 1, 84], [59, 82, 139], [33, 145, 140], [94, 201, 98], [253, 231, 37]],
      cividis: [[0, 32, 77], [43, 73, 113], [115, 113, 105], [180, 162, 83], [255, 233, 69]],
      magma: [[0, 0, 4], [61, 15, 111], [140, 41, 129], [221, 73, 104], [252, 253, 191]]
    };
    return palettes[name] || palettes.turbo;
  }

  function mapColor(value, vmin, vmax, paletteName) {
    if (!Number.isFinite(value)) return "rgba(0,0,0,0)";
    const t = vmax === vmin ? 0.5 : Math.max(0, Math.min(1, (value - vmin) / (vmax - vmin)));
    const stops = colorStops(paletteName);
    const scaled = t * (stops.length - 1);
    const index = Math.min(stops.length - 2, Math.floor(scaled));
    const local = scaled - index;
    const a = stops[index];
    const b = stops[index + 1];
    const rgb = a.map((start, channel) => Math.round(start + (b[channel] - start) * local));
    return `rgb(${rgb[0]},${rgb[1]},${rgb[2]})`;
  }

  function activeFieldStats() {
    return data.visualizationConfig?.nodemapBaseLayer?.fieldStats?.[state.overlay] || {
      min: 0,
      max: 1,
      mean: 0.5,
      std: 0.25,
      p01: 0,
      p99: 1
    };
  }

  function activeScale() {
    const stats = activeFieldStats();
    if (state.fieldScalePreset === "manual") {
      return {
        vmin: Number(state.fieldVmin),
        vmax: Number(state.fieldVmax),
        label: `manual ${formatNumber(state.fieldVmin, 4)} to ${formatNumber(state.fieldVmax, 4)}`
      };
    }
    const sigmaMap = { sigma1: 1, sigma2: 2, sigma3: 3 };
    const sigma = state.fieldScalePreset === "customSigma"
      ? Number(state.fieldSigma || 2)
      : sigmaMap[state.fieldScalePreset];
    if (sigma) {
      return {
        vmin: stats.mean - sigma * stats.std,
        vmax: stats.mean + sigma * stats.std,
        label: `mean +/- ${formatNumber(sigma, 1)} sigma`
      };
    }
    return {
      vmin: stats.p01 ?? stats.min,
      vmax: stats.p99 ?? stats.max,
      label: "auto p01-p99"
    };
  }

  function syncScaleInputs(scale) {
    els.fieldScalePreset.value = state.fieldScalePreset;
    els.fieldSigma.value = state.fieldSigma;
    els.fieldVmin.value = formatNumber(scale.vmin, 6);
    els.fieldVmax.value = formatNumber(scale.vmax, 6);
  }

  function renderLiveField() {
    const canvas = els.fieldCanvas;
    const context = canvas.getContext("2d");
    const rows = fieldRows();
    const xIndex = pointColumnIndex("x");
    const yIndex = pointColumnIndex("y");
    const valueIndex = pointColumnIndex(state.overlay);
    const scale = activeScale();
    syncScaleInputs(scale);
    canvas.dataset.activeField = state.overlay;
    canvas.dataset.activeColormap = state.fieldColoring;
    canvas.dataset.vmin = String(scale.vmin);
    canvas.dataset.vmax = String(scale.vmax);

    context.clearRect(0, 0, canvas.width, canvas.height);
    context.fillStyle = "#111719";
    context.fillRect(0, 0, canvas.width, canvas.height);

    if (xIndex < 0 || yIndex < 0 || valueIndex < 0 || !rows.length) {
      context.fillStyle = "#dbeff0";
      context.font = "14px Cascadia Mono, Consolas, monospace";
      context.fillText("No live nodemap data available", 32, 48);
      return;
    }

    const box = fieldPlotBox();
    const pointSize = Math.max(1.4, Math.min(3.2, Math.sqrt((box.plotWidth * box.plotHeight) / rows.length) * 0.72));
    rows.forEach((row) => {
      const x = Number(row[xIndex]);
      const y = Number(row[yIndex]);
      const value = Number(row[valueIndex]);
      const px = box.plotX + ((x - box.xRange[0]) / (box.xRange[1] - box.xRange[0])) * box.plotWidth;
      const py = box.plotY + box.plotHeight - ((y - box.yRange[0]) / (box.yRange[1] - box.yRange[0])) * box.plotHeight;
      context.fillStyle = mapColor(value, scale.vmin, scale.vmax, state.fieldColoring);
      context.fillRect(px - pointSize / 2, py - pointSize / 2, pointSize, pointSize);
    });
  }

  function overlayVisible(kind) {
    if (state.setupOverlayMode === "combined") {
      return kind === "annulus" ? state.showAnnulus
        : kind === "integrals" ? state.showLinePaths
          : state.showDetectionWindow;
    }
    return state.setupOverlayMode === kind
      && (kind === "annulus" ? state.showAnnulus : kind === "integrals" ? state.showLinePaths : state.showDetectionWindow);
  }

  function polarScreenPoint(center, radius, angleRad) {
    return {
      x: center.x + Math.cos(angleRad) * radius,
      y: center.y - Math.sin(angleRad) * radius
    };
  }

  function annulusSectorPath(center, innerRadius, outerRadius, crackAngleRad, angleGapDeg) {
    const gapRad = Math.max(0, Math.min(170, Number(angleGapDeg || 0))) * Math.PI / 180;
    const startAngle = crackAngleRad - Math.PI + gapRad;
    const endAngle = crackAngleRad + Math.PI - gapRad;
    const span = Math.max(0.001, endAngle - startAngle);
    const largeArc = span > Math.PI ? 1 : 0;
    const outerStart = polarScreenPoint(center, outerRadius, startAngle);
    const outerEnd = polarScreenPoint(center, outerRadius, endAngle);
    const innerEnd = polarScreenPoint(center, innerRadius, endAngle);
    const innerStart = polarScreenPoint(center, innerRadius, startAngle);

    return [
      `M ${outerStart.x} ${outerStart.y}`,
      `A ${outerRadius} ${outerRadius} 0 ${largeArc} 0 ${outerEnd.x} ${outerEnd.y}`,
      `L ${innerEnd.x} ${innerEnd.y}`,
      `A ${innerRadius} ${innerRadius} 0 ${largeArc} 1 ${innerStart.x} ${innerStart.y}`,
      "Z"
    ].join(" ");
  }

  function renderContours() {
    renderLiveField();
    renderSetupGeometry();
    applyFieldZoom();
    applyFeatureVisibility();
  }

  function renderSetupGeometry() {
    const frame = activeFrame();
    const raw = frame.raw || {};
    const observed = raw.crackTipEstimate || { x: frame.a - frame.dx, y: frame.tipY - frame.dy, angle: frame.angle };
    const corrected = raw.correctedCrackTipEstimate || { x: frame.a, y: frame.tipY, angle: frame.angle };
    const observedPoint = mapFieldPoint(observed.x, observed.y);
    const tip = mapFieldPoint(corrected.x, corrected.y);
    const angleRad = (Number(corrected.angle || 0) * Math.PI) / 180;
    const axisLength = mmToScreen(3.4);
    const axisEnd = {
      x: tip.x + Math.cos(angleRad) * axisLength,
      y: tip.y - Math.sin(angleRad) * axisLength
    };
    const normalEnd = {
      x: tip.x - Math.sin(angleRad) * axisLength * 0.55,
      y: tip.y - Math.cos(angleRad) * axisLength * 0.55
    };
    const minRadius = Number($("#minRadius").value || 0.35);
    const maxRadius = Number($("#maxRadius").value || 2.8);
    const angleGap = Number($("#angleGap").value || 20);
    const pathCount = Number($("#pathCount").value || 6);
    const detection = data.visualizationConfig?.crackDetectionDefaults || {};
    const detectionSize = Number(detection.detection_window_size_mm || 40);
    const detectionRadius = Number(detection.angle_detection_radius_mm || 10);
    const windowSize = mmToScreen(detectionSize);
    const angleRadius = mmToScreen(detectionRadius);

    const markers = `
      <g data-feature="crack-tip-markers">
        <circle class="tip-marker observed-tip" cx="${observedPoint.x}" cy="${observedPoint.y}" r="6" />
        <circle class="tip-marker corrected-tip" cx="${tip.x}" cy="${tip.y}" r="7" />
        <path class="correction-vector" d="M${observedPoint.x} ${observedPoint.y} L${tip.x} ${tip.y}" />
      </g>
      <g data-feature="crack-tip-axis">
        <path class="crack-frame-line tangent" d="M${tip.x} ${tip.y} L${axisEnd.x} ${axisEnd.y}" />
        <path class="crack-frame-line normal" d="M${tip.x} ${tip.y} L${normalEnd.x} ${normalEnd.y}" />
      </g>
      <g data-feature="crack-path">
        <path class="crack-path-line" d="M${tip.x - Math.cos(angleRad) * axisLength * 1.2} ${tip.y + Math.sin(angleRad) * axisLength * 1.2} L${axisEnd.x} ${axisEnd.y}" />
      </g>
    `;

    const annulus = overlayVisible("annulus") ? `
      <g data-feature="annulus-overlay" data-testid="williams-fit-annulus">
        <path class="williams-annulus-domain" d="${annulusSectorPath(tip, mmToScreen(minRadius), mmToScreen(maxRadius), angleRad, angleGap)}" />
        <circle class="annulus-ring outer" cx="${tip.x}" cy="${tip.y}" r="${mmToScreen(maxRadius)}" />
        <circle class="annulus-ring inner" cx="${tip.x}" cy="${tip.y}" r="${mmToScreen(minRadius)}" />
        <path class="annulus-gap-edge" d="M${tip.x} ${tip.y} L${polarScreenPoint(tip, mmToScreen(maxRadius), angleRad - Math.PI + angleGap * Math.PI / 180).x} ${polarScreenPoint(tip, mmToScreen(maxRadius), angleRad - Math.PI + angleGap * Math.PI / 180).y}" />
        <path class="annulus-gap-edge" d="M${tip.x} ${tip.y} L${polarScreenPoint(tip, mmToScreen(maxRadius), angleRad + Math.PI - angleGap * Math.PI / 180).x} ${polarScreenPoint(tip, mmToScreen(maxRadius), angleRad + Math.PI - angleGap * Math.PI / 180).y}" />
      </g>
    ` : "";

    const paths = overlayVisible("integrals") ? `
      <g data-feature="line-integral-paths">
        ${Array.from({ length: pathCount }, (_, index) => {
          const radius = minRadius + ((maxRadius - minRadius) * (index + 1)) / Math.max(1, pathCount);
          const size = mmToScreen(radius) * 2;
          return `<rect class="integral-path" x="${tip.x - size / 2}" y="${tip.y - size / 2}" width="${size}" height="${size}" />`;
        }).join("")}
      </g>
    ` : "";

    const detectionWindow = overlayVisible("detection-window") ? `
      <g data-feature="detection-window">
        <rect class="detection-window" x="${observedPoint.x - windowSize / 2}" y="${observedPoint.y - windowSize / 2}" width="${windowSize}" height="${windowSize}" />
        <circle class="angle-radius" cx="${observedPoint.x}" cy="${observedPoint.y}" r="${angleRadius}" />
      </g>
    ` : "";

    els.setupGeometryLayer.innerHTML = `${detectionWindow}${annulus}${paths}${markers}`;
  }

  function renderConfigLenses() {
    const minRadius = Number($("#minRadius").value || 0);
    const maxRadius = Number($("#maxRadius").value || 0);
    const angleGap = Number($("#angleGap").value || 0);
    const pathCount = Number($("#pathCount").value || 0);
    const lineDefaults = data.visualizationConfig?.lineIntegralDefaults || {};
    const detection = data.visualizationConfig?.crackDetectionDefaults || {};

    els.configLenses.innerHTML = `
      <article class="config-lens" data-testid="detection-lens">
        <div>
          <span class="section-label">crack detection lens</span>
          <strong>${detection.detection_window_size_mm || 40} mm window</strong>
        </div>
        <dl>
          <dt>resolution</dt><dd>${detection.detection_input_resolution_px || 256} px</dd>
          <dt>angle r.</dt><dd>${detection.angle_detection_radius_mm || 10} mm</dd>
          <dt>side</dt><dd>${activeExperiment().id.includes("-left") ? "left" : "right"}</dd>
        </dl>
      </article>
      <article class="config-lens" data-testid="annulus-lens">
        <div>
          <span class="section-label">Williams annulus lens</span>
          <strong>${formatNumber(minRadius, 2)}-${formatNumber(maxRadius, 2)} mm</strong>
        </div>
        <dl>
          <dt>angle gap</dt><dd>${angleGap} deg</dd>
          <dt>purpose</dt><dd>fit domain only</dd>
        </dl>
      </article>
      <article class="config-lens" data-testid="integral-lens">
        <div>
          <span class="section-label">line integral lens</span>
          <strong>${pathCount} contour paths</strong>
        </div>
        <dl>
          <dt>nodes</dt><dd>${lineDefaults.number_of_nodes || 100}</dd>
          <dt>tick</dt><dd>${lineDefaults.integral_tick_size_mm || 0.01} mm</dd>
          <dt>mask tol.</dt><dd>${lineDefaults.mask_tolerance || 2}</dd>
        </dl>
      </article>
    `;
  }

  function renderMetrics() {
    const frame = activeFrame();
    const sourceMetrics = frame.raw && frame.raw.metrics ? frame.raw.metrics : [];
    const metrics = sourceMetrics.length
      ? sourceMetrics.map((metric) => ({
        label: `${metric.label} ${metric.methodSource}`,
        value: formatNumber(metric.value, Math.abs(metric.value) < 10 ? 2 : 1),
        unit: metric.unit
      })).concat([
        { label: "Williams Error_xy", value: formatNumber(frame.residual, 3), unit: "1" },
        { label: "crack angle", value: formatNumber(frame.angle || 0, 1), unit: "deg" }
      ])
      : [];

    els.metricGrid.innerHTML = metrics.map((metric) => `
      <article class="metric">
        <span>${metric.label}</span>
        <strong>${metric.value}</strong>
        <small>${metric.unit}</small>
      </article>
    `).join("");
  }

  function formatEvidenceValue(value, digits = 3) {
    if (value == null || !Number.isFinite(Number(value))) return "n/a";
    const numeric = Number(value);
    const precision = Math.abs(numeric) >= 100 ? 1 : digits;
    return numeric.toFixed(precision);
  }

  function formatEvidenceRange(start, end) {
    return `${formatEvidenceValue(start)} to ${formatEvidenceValue(end)}`;
  }

  function renderMethodEvidence() {
    const frame = activeFrame();
    const evidence = frame.raw?.methodEvidence || {};
    const mode = state.methodEvidenceMode;
    const titles = {
      williamsTerms: "Williams terms",
      pathStability: "Path stability",
      integralSummary: "Integral summary"
    };
    els.methodEvidenceTitle.textContent = titles[mode] || titles.williamsTerms;
    els.methodEvidenceMode.value = mode;

    if (mode === "williamsTerms") {
      const terms = evidence.williamsTerms || [];
      const families = ["a_n", "b_n", "c_n"];
      els.methodEvidenceTable.innerHTML = `
        <p class="evidence-note">Williams terms are shown by family. They are not aggregated because units depend on term order.</p>
        <table>
          <thead><tr><th>family</th><th>source values</th></tr></thead>
          <tbody>
            ${families.map((family) => {
              const familyTerms = terms.filter((term) => term.family === family);
              return `
                <tr>
                  <td>${family}</td>
                  <td>${familyTerms.map((term) => `<span class="mini-term">${term.term}=${formatEvidenceValue(term.value, 2)}</span>`).join(" ")}</td>
                </tr>
              `;
            }).join("")}
          </tbody>
        </table>
      `;
      return;
    }

    if (mode === "pathStability") {
      const rows = evidence.pathStability || [];
      els.methodEvidenceTable.innerHTML = `
        <table>
          <thead><tr><th>quantity</th><th>mean</th><th>q10-q90</th><th>min-max</th></tr></thead>
          <tbody>
            ${rows.map((row) => `
              <tr>
                <td>${row.label}<small>${row.unit}</small></td>
                <td>${formatEvidenceValue(row.mean)}</td>
                <td>${formatEvidenceRange(row.q10, row.q90)}</td>
                <td>${formatEvidenceRange(row.minimum, row.maximum)}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      `;
      return;
    }

    const rows = evidence.integralSummary || [];
    els.methodEvidenceTable.innerHTML = `
      <table>
        <thead><tr><th>quantity</th><th>mean</th><th>median</th><th>wo outliers</th></tr></thead>
        <tbody>
          ${rows.map((row) => `
            <tr>
              <td>${row.label}<small>${row.unit}</small></td>
              <td>${formatEvidenceValue(row.mean)}</td>
              <td>${formatEvidenceValue(row.median)}</td>
              <td>${formatEvidenceValue(row.mean_wo_outliers)}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    `;
  }

  function renderMethods() {
    els.methodStack.innerHTML = data.methods.map((method) => `
      <article class="method-card">
        <div>
          <span>${method.source}</span>
          <strong>${method.label}</strong>
        </div>
        <em>${method.value}</em>
      </article>
    `).join("");
  }

  function renderWarnings() {
    const frame = activeFrame();
    const warnings = frame.raw && frame.raw.warningIds && data.warningMap
      ? frame.raw.warningIds.map((id) => data.warningMap.get(id)).filter(Boolean)
      : data.warnings;
    els.warningList.innerHTML = warnings.map((warning) => {
      if (typeof warning === "string") return `<li>${warning}</li>`;
      return `<li><strong>${warning.label}</strong>: ${warning.detail}</li>`;
    }).join("");
  }

  function renderFrames() {
    els.frameRows.innerHTML = allFrames().map(({ experiment, frame }) => {
      const active = frame.frame === state.frame && experiment.id === state.experimentId ? " class=\"is-active\"" : "";
      return `
        <tr${active} data-experiment="${experiment.id}" data-frame="${frame.frame}" tabindex="0" data-testid="frame-row">
          <td>${frame.frame}</td>
          <td>${formatNumber(frame.cycles, 0)}</td>
          <td>${formatNumber(frame.a, 2)} mm</td>
          <td>${frame.kiSource}</td>
          <td>${frame.kiiSource}</td>
          <td>${frame.j == null ? "not run" : `${formatNumber(frame.j, 2)} ${frame.jUnit || "N/mm"}`}</td>
          <td>${formatNumber(frame.residual, 3)}</td>
          <td><span class="badge ${frame.status === "ok" ? "is-good" : "is-risk"}">${frame.status}</span></td>
        </tr>
      `;
    }).join("");
  }

  function renderGraphArtifactControls() {
    const artifacts = graphArtifacts();
    const active = activeGraphArtifact();
    if (!artifacts.some((artifact) => artifact.id === state.graphArtifactId)) {
      state.graphArtifactId = active.id;
    }
    if (!activeGraphNodeTypes().includes(state.selectedGraphNode)) {
      state.selectedGraphNode = activeGraphNodeTypes()[0] || "InputRecord";
    }
    els.graphArtifactSelect.innerHTML = artifacts.map((artifact) => {
      const selected = artifact.id === state.graphArtifactId ? " selected" : "";
      return `<option value="${artifact.id}"${selected}>${artifact.label}</option>`;
    }).join("");
    els.graphArtifactSummary.innerHTML = `
      <strong>${active.method || "method graph"}</strong>
      <span>${active.nodeCount || activeGraphNodeTypes().length} nodes, ${active.edgeCount || (active.edges || []).length} edges</span>
      <code>${active.path || activeGraphSummary().path || "graph JSON not available"}</code>
    `;
  }

  function renderAnalysisGraph() {
    const artifact = activeGraphArtifact();
    const nodes = activeGraphNodeTypes();
    const details = activeGraphNodeDetails();
    const edges = artifact?.edges || [];
    const laneOrder = [
      "InputRecord",
      "MethodMetadata",
      "NormalizedConfiguration",
      "CrackTipEstimateResult",
      "CrackTipFrame",
      "AnalysisRun",
      "ResultRecord",
      "ResultQuantity",
      "ArtifactRef"
    ];
    const columns = [
      ["InputRecord", "MethodMetadata", "NormalizedConfiguration"],
      ["CrackTipEstimateResult", "CrackTipFrame"],
      ["AnalysisRun"],
      ["ResultRecord"],
      ["ResultQuantity", "ArtifactRef"]
    ];
    const positions = {};
    columns.forEach((column, columnIndex) => {
      const visible = column.filter((nodeType) => nodes.includes(nodeType));
      visible.forEach((nodeType, rowIndex) => {
        const y = 100 + rowIndex * 106 + Math.max(0, 2 - visible.length) * 24;
        positions[nodeType] = [70 + columnIndex * 195, y];
      });
    });
    nodes
      .filter((nodeType) => !positions[nodeType])
      .sort((a, b) => laneOrder.indexOf(a) - laneOrder.indexOf(b))
      .forEach((nodeType, index) => {
        positions[nodeType] = [70 + (index % 5) * 195, 84 + Math.floor(index / 5) * 112];
      });
    const edgeMarkup = edges.map((edge) => {
      const from = positions[edge.from];
      const to = positions[edge.to];
      if (!from || !to) return "";
      const active = edge.from === state.selectedGraphNode || edge.to === state.selectedGraphNode;
      const midX = (from[0] + to[0]) / 2;
      const midY = (from[1] + to[1]) / 2;
      return `
        <path class="graph-edge${active ? " is-active" : ""}" d="M${from[0] + 70} ${from[1]} C${midX} ${from[1]}, ${midX} ${to[1]}, ${to[0] - 70} ${to[1]}" />
        ${active ? `<text class="graph-edge-label" x="${midX}" y="${midY - 7}">${edge.label}</text>` : ""}
      `;
    }).join("");
    const nodeMarkup = nodes.map((nodeType) => {
      const [x, y] = positions[nodeType] || [70, 70];
      const detail = details[nodeType] || {};
      const active = nodeType === state.selectedGraphNode;
      const color = detail.color || "#374151";
      const title = nodeType.replace(/([a-z])([A-Z])/g, "$1 $2");
      return `
        <g class="graph-node${active ? " is-active" : ""}" transform="translate(${x - 70} ${y - 27})">
          <rect class="graph-node-hit" data-node-type="${nodeType}" tabindex="0" role="button" aria-label="${nodeType}" width="140" height="54" rx="8" fill="${active ? color : "#ffffff"}" stroke="${color}" />
          <circle cx="17" cy="27" r="5" fill="${active ? "#ffffff" : color}" />
          <text x="30" y="23">${title}</text>
          <text class="graph-node-subtitle" x="30" y="39">${detail.surface || "graph node"}</text>
        </g>
      `;
    }).join("");

    els.analysisGraph.innerHTML = `
      <svg viewBox="0 0 940 390" role="img" aria-label="${artifact?.label || "Separate proof graph"} node types">
        <defs>
          <marker id="graphArrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
            <path d="M0 0 10 5 0 10z" fill="#7a8b94"></path>
          </marker>
        </defs>
        <rect x="10" y="14" width="920" height="362" rx="8" fill="#f8fbfc" stroke="#cbd6dc" />
        <text class="graph-band-label" x="42" y="44">separate proof inputs</text>
        <text class="graph-band-label" x="265" y="44">crack-tip frame</text>
        <text class="graph-band-label" x="465" y="44">method execution</text>
        <text class="graph-band-label" x="648" y="44">result envelope</text>
        <text class="graph-artifact-label" x="42" y="364">${artifact?.label || "proof graph"} - ${artifact?.nodeCount || nodes.length} nodes - ${artifact?.edgeCount || edges.length} edges</text>
        <g>${edgeMarkup}</g>
        <g>${nodeMarkup}</g>
      </svg>
    `;
  }

  function renderSourceEvidence() {
    const frame = activeFrame();
    const paths = frame.raw?.sourcePaths || {};
    const graph = activeGraphSummary();
    const artifact = activeGraphArtifact();
    const entries = [
      ["nodemap", paths.nodemap || "not available"],
      ["result CSV", paths.resultCsv || "not available"],
      ["text output", paths.resultText || "not available"],
      ["graph JSON", graph.path ? `${graph.path} (${graph.scope || "separate proof graph"})` : "not available"]
    ];
    els.sourceEvidence.innerHTML = `
      <div>
        <span class="section-label">two source scopes</span>
        <strong>${data.dataPolicy || "actual CrackPy data"}</strong>
        <p class="scope-note">Frame values come from Dummy2 fixture outputs. The selected ${artifact?.method || "method"} graph is a separate proof artifact and is shown only as a frontend-facing node demonstrator.</p>
      </div>
      <dl>
        ${entries.map(([label, value]) => `<dt>${label}</dt><dd>${value}</dd>`).join("")}
      </dl>
    `;
  }

  function renderNodeSurfaceMatrix() {
    const surfaceMap = {
      InputRecord: "source evidence + nodemap selector",
      MethodMetadata: "method stack + provenance snippet",
      NormalizedConfiguration: "setup lenses",
      CrackTipFrame: "setup geometry layer",
      CrackTipEstimateResult: "tip/delta readouts",
      AnalysisRun: "start experiment + frame table",
      ResultRecord: "result inspector",
      ResultQuantity: "metric cards + method evidence",
      ArtifactRef: "provenance JSON snippet"
    };
    const nodes = activeGraphNodeTypes();
    const artifact = activeGraphArtifact();
    els.nodeSurfaceMatrix.innerHTML = `
      <div>
        <span class="section-label">frontend-facing nodes</span>
        <strong>${nodes.length} graph node classes represented for ${artifact?.label || "the active proof graph"}</strong>
      </div>
      <div class="node-surface-grid">
        ${nodes.map((nodeType) => `
          <article>
            <code>${nodeType}</code>
            <span>${surfaceMap[nodeType] || "provenance graph"}</span>
          </article>
        `).join("")}
      </div>
    `;
  }

  function renderProvenance() {
    renderGraphArtifactControls();
    renderAnalysisGraph();
    renderSourceEvidence();
    renderNodeSurfaceMatrix();

    els.provenanceFlow.innerHTML = data.provenance.map((step, index) => `
      <article class="provenance-step">
        <span class="step-node">${index + 1}</span>
        <div>
          <strong>${step.title}</strong>
          <span>${step.detail}</span>
        </div>
      </article>
    `).join("");

    els.graphNodeChips.innerHTML = activeGraphNodeTypes().map((nodeType) => {
      const detail = activeGraphNodeDetails()[nodeType] || {};
      const active = nodeType === state.selectedGraphNode ? " is-active" : "";
      const style = nodeType === state.selectedGraphNode && detail.color
        ? ` style="background:${detail.color};border-color:${detail.color}"`
        : "";
      return `<button type="button" class="graph-chip${active}" data-node-type="${nodeType}"${style}>${nodeType}</button>`;
    }).join("");
    renderNodeInspector();

    const frame = activeFrame();
    const methodId = frame.kiSource === "Bueckner-Chen"
      ? "crackpy.fracture.bueckner_chen_integral"
      : "crackpy.fracture.williams_fit";
    els.provenanceBadge.textContent = activeGraphArtifact()?.method || "separate graph proof";
    const snippet = {
      method_id: methodId,
      data_ref: els.nodemapSelect.value,
      frame: frame.frame,
      quantities: {
        K_I: { value: frame.ki, unit: "MPa*m^{1/2}", source: frame.kiSource },
        K_II: { value: frame.kii, unit: "MPa*m^{1/2}", source: frame.kiiSource },
        J: frame.j == null
          ? { value: null, unit: "N/mm", source: "not run" }
          : { value: frame.j, unit: frame.jUnit || "N/mm", source: "J-integral" }
      },
      crack_tip: {
        estimate_mm: frame.raw ? [frame.raw.crackTipEstimate.x, frame.raw.crackTipEstimate.y] : null,
        corrected_estimate_mm: frame.raw ? [frame.raw.correctedCrackTipEstimate.x, frame.raw.correctedCrackTipEstimate.y] : null,
        correction_delta_mm: frame.raw ? [frame.raw.correctionDelta.dx, frame.raw.correctionDelta.dy] : null
      },
      actual_sources: frame.raw?.sourcePaths || {},
      graph_artifact: activeGraphArtifact()?.id || null,
      graph_note: activeGraphSummary()?.scope || "Graph panel is a separate proof export, not the selected frame graph."
    };
    els.provenanceSnippet.textContent = JSON.stringify(snippet, null, 2);
  }

  function renderNodeInspector() {
    const nodeType = state.selectedGraphNode;
    const detail = activeGraphNodeDetails()[nodeType] || {
      surface: "graph node",
      role: "No details available.",
      keyFields: [],
      example: nodeType
    };
    els.nodeInspectorTitle.textContent = `${nodeType} - ${detail.surface || "graph node"}`;
    els.nodeInspectorRole.textContent = detail.role || "";
    const fields = [
      ["example", detail.example || nodeType],
      ["fields", (detail.keyFields || []).join(", ")],
      ["node count", detail.actualNodeCount || 1],
      ["scope", activeGraphSummary()?.scope || "separate proof graph"],
      ["artifact", activeGraphArtifact()?.label || "proof graph"]
    ];
    els.nodeInspectorFields.innerHTML = fields.map(([term, value]) => (
      `<dt>${term}</dt><dd>${value}</dd>`
    )).join("");
  }

  function renderRunState() {
    const frame = activeFrame();
    els.activeFrameLabel.textContent = frame.frame;
    els.tipReadout.textContent = `x=${formatNumber(frame.a, 2)} mm, y=${formatNumber(frame.tipY, 2)} mm`;
    els.deltaReadout.textContent = `dx=${formatNumber(frame.dx, 3)} mm, dy=${formatNumber(frame.dy, 3)} mm`;
    els.overlayReadout.textContent = `${state.overlay}, ${state.fieldColoring}`;
    els.fieldScaleReadout.textContent = `${activeScale().label}; vmin=${formatNumber(els.fieldCanvas.dataset.vmin, 4)}, vmax=${formatNumber(els.fieldCanvas.dataset.vmax, 4)}`;
    els.setupGeometryReadout.textContent = `${state.setupOverlayMode}, zoom ${formatNumber(state.fieldZoom, 2)}x`;
    els.qualityBadge.textContent = frame.status === "ok" ? "fixture ok" : "review";
    els.qualityBadge.className = `badge ${frame.status === "ok" ? "is-good" : "is-risk"}`;
    const frameIndex = allFrames().findIndex(({ experiment, frame: candidate }) => (
      experiment.id === state.experimentId && candidate.frame === state.frame
    ));
    els.sideProgress.style.width = `${Math.round(((frameIndex + 1) / allFrames().length) * 100)}%`;

    if (state.running) {
      els.runBadge.textContent = "running";
      els.runBadge.className = "badge is-running";
      els.runMessage.textContent = "Advancing through actual CrackPy fixture result frames";
    } else {
      els.runBadge.textContent = "ready";
      els.runBadge.className = "badge is-ready";
      els.runMessage.textContent = `Frame ${frame.frame} selected; values are from actual fixture outputs`;
    }
  }

  function renderDebugPanel() {
    els.debugFeatureMatrix.innerHTML = featureDefinitions.map((feature) => `
      <label class="debug-toggle">
        <input type="checkbox" data-feature-toggle="${feature.key}" ${state.featureFlags[feature.key] ? "checked" : ""}>
        <span>${feature.label}</span>
        <code>${feature.key}</code>
      </label>
    `).join("");
    els.debugState.textContent = JSON.stringify(debugSnapshot(), null, 2);
  }

  function applyFeatureVisibility() {
    featureDefinitions.forEach((feature) => {
      const enabled = state.featureFlags[feature.key] !== false;
      $$(feature.selector).forEach((element) => {
        element.hidden = !enabled;
        element.setAttribute("aria-hidden", enabled ? "false" : "true");
        element.style.display = enabled ? "" : "none";
        if ("inert" in element) {
          element.inert = !enabled;
        }
      });
    });
  }

  function advanceFrame() {
    const frames = allFrames();
    const index = frames.findIndex(({ experiment, frame }) => (
      experiment.id === state.experimentId && frame.frame === state.frame
    ));
    const next = frames[(index + 1) % frames.length];
    state.experimentId = next.experiment.id;
    state.frame = next.frame.frame;
    renderAll();
    return debugSnapshot();
  }

  function resetFeatureFlags() {
    featureDefinitions.forEach((feature) => {
      state.featureFlags[feature.key] = true;
    });
    renderAll();
  }

  function debugSnapshot() {
    const frame = activeFrame();
    return {
      experimentId: state.experimentId,
      frame: state.frame,
      overlay: state.overlay,
      fieldColoring: state.fieldColoring,
      fieldScalePreset: state.fieldScalePreset,
      fieldSigma: Number(state.fieldSigma),
      fieldVmin: Number(els.fieldCanvas.dataset.vmin),
      fieldVmax: Number(els.fieldCanvas.dataset.vmax),
      fieldZoom: Number(state.fieldZoom),
      setupOverlayMode: state.setupOverlayMode,
      methodEvidenceMode: state.methodEvidenceMode,
      graphArtifactId: state.graphArtifactId,
      showLinePaths: state.showLinePaths,
      showAnnulus: state.showAnnulus,
      showDetectionWindow: state.showDetectionWindow,
      selectedGraphNode: state.selectedGraphNode,
      running: state.running,
      featureFlags: { ...state.featureFlags },
      activeSources: frame.raw?.sourcePaths || {},
      graphScope: activeGraphSummary()?.scope || null,
      graphArtifactPath: activeGraphArtifact()?.path || null,
      graphArtifactCount: graphArtifacts().length
    };
  }

  function runDebugAssertions() {
    const checks = [
      ["live field canvas is actual data", () => fieldRows().length > 0 && els.fieldCanvas.dataset.activeField === state.overlay],
      ["field scale is finite", () => Number.isFinite(Number(els.fieldCanvas.dataset.vmin)) && Number.isFinite(Number(els.fieldCanvas.dataset.vmax))],
      ["actual source rows are present", () => data.actualDataSources.some((source) => source.includes("results_auto_integral_probs.csv"))],
      ["active frame has source paths", () => Boolean(activeFrame().raw?.sourcePaths?.nodemap)],
      ["method evidence is source-backed", () => (activeFrame().raw?.methodEvidence?.williamsTerms || []).length > 0],
      ["node surface matrix is rendered", () => els.nodeSurfaceMatrix.textContent.includes("ResultQuantity")],
      ["setup geometry renders visible nodes", () => els.setupGeometryLayer.children.length > 0],
      ["graph is marked as separate proof", () => String(activeGraphSummary()?.scope || "").includes("separate")],
      ["graph artifact selector is wired", () => graphArtifacts().length >= 1 && Boolean(state.graphArtifactId)],
      ["debug API is exposed", () => Boolean(window.CrackPyLabDebug?.getState)]
    ];
    const results = checks.map(([label, predicate]) => {
      let pass = false;
      try {
        pass = Boolean(predicate());
      } catch (error) {
        pass = false;
      }
      return { label, pass };
    });
    const failed = results.filter((result) => !result.pass);
    els.debugAssertionStatus.textContent = failed.length ? `FAIL ${failed.length}/${results.length}` : `PASS ${results.length}/${results.length}`;
    els.debugAssertionStatus.className = failed.length ? "debug-fail" : "debug-pass";
    els.debugState.textContent = JSON.stringify({ assertions: results, state: debugSnapshot() }, null, 2);
    return results;
  }

  function renderAll() {
    renderExperimentControls();
    renderContours();
    renderConfigLenses();
    renderMetrics();
    renderMethodEvidence();
    renderMethods();
    renderWarnings();
    renderFrames();
    renderProvenance();
    renderRunState();
    renderDebugPanel();
    applyFeatureVisibility();
  }

  function bindEvents() {
    $("#pathCount").value = defaultPathCount;
    $("#minRadius").value = defaultWilliams.min_radius_mm || 5;
    $("#maxRadius").value = defaultWilliams.max_radius_mm || 10;
    $("#angleGap").value = defaultWilliams.angle_gap_deg || 20;

    $$(".nav-item").forEach((button) => {
      button.addEventListener("click", () => {
        $$(".nav-item").forEach((candidate) => candidate.classList.toggle("is-active", candidate === button));
        const targets = {
          workspace: ".setup-panel",
          experiments: ".timeline-panel",
          detection: ".field-panel",
          analysis: ".result-panel",
          results: ".timeline-panel",
          provenance: ".provenance-panel"
        };
        const target = $(targets[button.dataset.panel] || ".setup-panel");
        target?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    });

    els.experimentSelect.addEventListener("change", (event) => {
      state.experimentId = event.target.value;
      state.frame = activeExperiment().defaultFrame;
      renderAll();
    });

    els.sideSelect.addEventListener("change", (event) => {
      const side = event.target.value;
      const candidate = data.experiments.find((experiment) => experiment.id.includes(`-${side}`));
      if (candidate) {
        state.experimentId = candidate.id;
        state.frame = candidate.defaultFrame;
        renderAll();
      }
    });

    els.nodemapSelect.addEventListener("change", (event) => {
      const experiment = activeExperiment();
      const candidate = experiment.frames.find((frame) => frame.raw?.imageName === event.target.value);
      if (candidate) {
        state.frame = candidate.frame;
        renderAll();
      } else {
        els.runMessage.textContent = "Selected nodemap is listed for this fixture family; no separate result row was found";
      }
    });

    els.materialSelect.addEventListener("change", () => {
      els.runMessage.textContent = "Material selector is bound to the fixture context shown in the current result rows";
    });

    els.startRunButton.addEventListener("click", () => {
      state.running = true;
      renderRunState();
      window.setTimeout(() => {
        state.running = false;
        advanceFrame();
      }, 900);
    });

    els.resetButton.addEventListener("click", () => {
      state.frame = activeExperiment().defaultFrame;
      state.running = false;
      state.correction = "actual";
      state.showLinePaths = true;
      state.showAnnulus = true;
      state.showDetectionWindow = true;
      state.setupOverlayMode = "combined";
      state.fieldZoom = 1;
      state.fieldColoring = data.visualizationConfig?.nodemapBaseLayer?.defaultColormap || "turbo";
      state.fieldScalePreset = "auto";
      state.fieldSigma = 2;
      state.fieldVmin = null;
      state.fieldVmax = null;
      state.graphArtifactId = graphArtifacts()[0]?.id || "legacy-graph";
      state.selectedGraphNode = "InputRecord";
      $("#pathCount").value = defaultPathCount;
      $("#minRadius").value = defaultWilliams.min_radius_mm || 5;
      $("#maxRadius").value = defaultWilliams.max_radius_mm || 10;
      $("#angleGap").value = defaultWilliams.angle_gap_deg || 20;
      els.showLinePaths.checked = state.showLinePaths;
      els.showAnnulus.checked = state.showAnnulus;
      els.showDetectionWindow.checked = state.showDetectionWindow;
      els.setupOverlayMode.value = state.setupOverlayMode;
      els.fieldZoom.value = state.fieldZoom;
      els.fieldColoring.value = state.fieldColoring;
      els.fieldScalePreset.value = state.fieldScalePreset;
      els.fieldSigma.value = state.fieldSigma;
      els.graphArtifactSelect.value = state.graphArtifactId;
      $$(".segment").forEach((button) => button.classList.toggle("is-active", button.dataset.correction === "symbolic"));
      renderAll();
    });

    $$(".segment").forEach((button) => {
      button.addEventListener("click", () => {
        state.correction = "actual";
        $$(".segment").forEach((candidate) => candidate.classList.toggle("is-active", candidate === button));
        renderRunState();
      });
    });

    $$(".tool").forEach((button) => {
      button.addEventListener("click", () => {
        state.overlay = button.dataset.overlay;
        $$(".tool").forEach((candidate) => candidate.classList.toggle("is-active", candidate === button));
        renderContours();
        renderRunState();
        renderDebugPanel();
      });
    });

    $$(".tab").forEach((button) => {
      button.addEventListener("click", () => {
        $$(".tab").forEach((candidate) => candidate.classList.toggle("is-active", candidate === button));
        $(".lab-grid").dataset.viewFilter = button.dataset.view;
      });
    });

    ["#pathCount", "#minRadius", "#maxRadius", "#angleGap"].forEach((selector) => {
      $(selector).addEventListener("input", () => {
        renderContours();
        renderConfigLenses();
        renderRunState();
        renderDebugPanel();
      });
    });

    [
      [els.showLinePaths, "showLinePaths"],
      [els.showAnnulus, "showAnnulus"],
      [els.showDetectionWindow, "showDetectionWindow"]
    ].forEach(([input, key]) => {
      input.addEventListener("change", (event) => {
        state[key] = event.target.checked;
        renderContours();
        renderRunState();
        renderDebugPanel();
      });
    });

    els.setupOverlayMode.addEventListener("change", (event) => {
      state.setupOverlayMode = event.target.value;
      renderContours();
      renderRunState();
      renderDebugPanel();
    });

    els.fieldColoring.addEventListener("change", (event) => {
      state.fieldColoring = event.target.value;
      renderContours();
      renderRunState();
      renderDebugPanel();
    });

    els.fieldScalePreset.addEventListener("change", (event) => {
      state.fieldScalePreset = event.target.value;
      if (state.fieldScalePreset === "manual") {
        state.fieldVmin = Number(els.fieldVmin.value);
        state.fieldVmax = Number(els.fieldVmax.value);
      }
      renderContours();
      renderRunState();
      renderDebugPanel();
    });

    els.fieldSigma.addEventListener("input", (event) => {
      state.fieldSigma = Number(event.target.value);
      state.fieldScalePreset = "customSigma";
      renderContours();
      renderRunState();
      renderDebugPanel();
    });

    [els.fieldVmin, els.fieldVmax].forEach((input) => {
      input.addEventListener("input", () => {
        state.fieldScalePreset = "manual";
        state.fieldVmin = Number(els.fieldVmin.value);
        state.fieldVmax = Number(els.fieldVmax.value);
        renderContours();
        renderRunState();
        renderDebugPanel();
      });
    });

    els.fieldZoom.addEventListener("input", (event) => {
      state.fieldZoom = Number(event.target.value);
      applyFieldZoom();
      renderRunState();
      renderDebugPanel();
    });

    els.methodEvidenceMode.addEventListener("change", (event) => {
      state.methodEvidenceMode = event.target.value;
      renderMethodEvidence();
      renderDebugPanel();
      applyFeatureVisibility();
    });

    els.graphArtifactSelect.addEventListener("change", (event) => {
      state.graphArtifactId = event.target.value;
      state.selectedGraphNode = activeGraphNodeTypes()[0] || "InputRecord";
      renderProvenance();
      renderDebugPanel();
      applyFeatureVisibility();
    });

    els.analysisGraph.addEventListener("click", (event) => {
      const node = event.target.closest("[data-node-type]");
      if (!node) return;
      state.selectedGraphNode = node.dataset.nodeType;
      renderProvenance();
      renderDebugPanel();
      applyFeatureVisibility();
    });

    els.graphNodeChips.addEventListener("click", (event) => {
      const chip = event.target.closest("[data-node-type]");
      if (!chip) return;
      state.selectedGraphNode = chip.dataset.nodeType;
      renderProvenance();
      renderDebugPanel();
      applyFeatureVisibility();
    });

    els.frameRows.addEventListener("click", (event) => {
      const row = event.target.closest("tr[data-frame]");
      if (!row) return;
      state.experimentId = row.dataset.experiment;
      state.frame = Number(row.dataset.frame);
      renderAll();
    });

    els.frameRows.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      const row = event.target.closest("tr[data-frame]");
      if (!row) return;
      event.preventDefault();
      state.experimentId = row.dataset.experiment;
      state.frame = Number(row.dataset.frame);
      renderAll();
    });

    els.exportButton.addEventListener("click", () => {
      els.runBadge.textContent = "exported";
      els.runBadge.className = "badge is-good";
      els.runMessage.textContent = "Prototype provenance JSON export was prepared";
      const blob = new Blob([els.provenanceSnippet.textContent], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `crackpy-frame-${activeFrame().frame}-prototype-provenance.json`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      els.provenanceSnippet.focus();
    });

    els.debugFeatureMatrix.addEventListener("change", (event) => {
      const toggle = event.target.closest("[data-feature-toggle]");
      if (!toggle) return;
      state.featureFlags[toggle.dataset.featureToggle] = toggle.checked;
      applyFeatureVisibility();
      renderDebugPanel();
    });

    els.resetFeatureFlags.addEventListener("click", resetFeatureFlags);
    els.runDebugAssertions.addEventListener("click", runDebugAssertions);
  }

  window.CrackPyLabDebug = {
    getState: () => debugSnapshot(),
    setState: (patch) => {
      Object.assign(state, patch || {});
      if (patch?.featureFlags) {
        Object.assign(state.featureFlags, patch.featureFlags);
      }
      renderAll();
      return debugSnapshot();
    },
    setFeature: (key, value) => {
      if (Object.hasOwn(state.featureFlags, key)) {
        state.featureFlags[key] = Boolean(value);
        applyFeatureVisibility();
        renderDebugPanel();
      }
      return debugSnapshot();
    },
    reset: () => {
      state.experimentId = data.experiments[0].id;
      state.frame = data.experiments[0].defaultFrame;
      state.overlay = "eps_eqv";
      state.fieldColoring = data.visualizationConfig?.nodemapBaseLayer?.defaultColormap || "turbo";
      state.fieldScalePreset = "auto";
      state.fieldSigma = 2;
      state.fieldVmin = null;
      state.fieldVmax = null;
      state.fieldZoom = 1;
      state.setupOverlayMode = "combined";
      state.showLinePaths = true;
      state.showAnnulus = true;
      state.showDetectionWindow = true;
      state.methodEvidenceMode = "williamsTerms";
      state.graphArtifactId = graphArtifacts()[0]?.id || "legacy-graph";
      state.selectedGraphNode = "InputRecord";
      state.running = false;
      resetFeatureFlags();
      return debugSnapshot();
    },
    resetFeatures: resetFeatureFlags,
    advanceRun: advanceFrame,
    runAssertions: runDebugAssertions
  };

  bindEvents();
  renderAll();
}());
