/* Dashboard 100% local: sin librerías externas, sin conexión a internet.
 * window.renderDashboard(data) es llamado desde Python (dashboard/window.py)
 * cada vez que se abre o refresca la ventana, con un JSON armado desde SQLite. */

const SVG_NS = "http://www.w3.org/2000/svg";

const COLOR_PAUSA = {
  almuerzo: "#e8a33d",
  merienda: "#3b6fd6",
  "baño": "#8a63d2",
  otra_cosa: "#9aa0ab",
  sin_clasificar: "#d64545",
};

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "text") node.textContent = v;
    else if (k === "html") node.innerHTML = v;
    else node.setAttribute(k, v);
  }
  for (const child of children) node.appendChild(child);
  return node;
}

function svg(tag, attrs = {}) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  return node;
}

/* Texto dentro de un SVG (para las marcas de números de los gráficos). */
function svgText(x, y, texto, attrs = {}) {
  const node = svg("text", {
    x,
    y,
    "font-size": 9,
    "font-family": "inherit",
    fill: "var(--text-muted)",
    ...attrs,
  });
  node.textContent = texto;
  return node;
}

function colorForScore(score) {
  if (score === null || score === undefined) return "var(--idle)";
  if (score >= 85) return "var(--good)";
  if (score >= 60) return "var(--warn)";
  return "var(--bad)";
}

function promedioHora(strings) {
  const minutos = strings.filter(Boolean).map((s) => {
    const [h, m] = s.split(":").map(Number);
    return h * 60 + m;
  });
  if (minutos.length === 0) return "—";
  const promedio = Math.round(minutos.reduce((a, b) => a + b, 0) / minutos.length);
  const h = Math.floor(promedio / 60)
    .toString()
    .padStart(2, "0");
  const m = (promedio % 60).toString().padStart(2, "0");
  return `${h}:${m}`;
}

function renderKPIs(data) {
  const contenedor = document.getElementById("kpis");
  contenedor.innerHTML = "";

  const dias = data.dias;
  const ultimos7 = dias.slice(-7);
  const horasSemana = ultimos7.reduce((acc, d) => acc + (d.horas_trabajadas || 0), 0);
  const idleSemana = ultimos7.reduce((acc, d) => acc + (d.horas_idle || 0), 0);
  const scoresValidos = dias.filter((d) => d.score !== null);
  const mejor = scoresValidos.reduce((a, b) => (b.score > (a?.score ?? -1) ? b : a), null);
  const peor = scoresValidos.reduce((a, b) => (b.score < (a?.score ?? 101) ? b : a), null);
  const totalPausas = data.pausas_confirmadas + data.pausas_inferidas;
  const pctConfirmadas = totalPausas ? Math.round((data.pausas_confirmadas / totalPausas) * 100) : 0;

  const tarjetas = [
    ["Score semanal", data.score_semanal !== null ? data.score_semanal.toFixed(0) : "—", colorForScore(data.score_semanal)],
    ["Horas trabajadas (7 días)", horasSemana.toFixed(1) + "h", null],
    ["Horas idle (7 días)", idleSemana.toFixed(1) + "h", null],
    ["Entrada promedio", promedioHora(dias.map((d) => d.entrada)), null],
    ["Salida promedio", promedioHora(dias.map((d) => d.salida)), null],
    ["Mejor día", mejor ? `${mejor.fecha} (${mejor.score})` : "—", null],
    ["Peor día", peor ? `${peor.fecha} (${peor.score})` : "—", null],
    ["Pausas confirmadas vs. inferidas", `${pctConfirmadas}% manual`, null],
  ];

  for (const [etiqueta, valor, color] of tarjetas) {
    const valorEl = el("div", { class: "valor", text: valor });
    if (color) valorEl.style.color = color;
    contenedor.appendChild(
      el("div", { class: "kpi" }, [valorEl, el("div", { class: "etiqueta", text: etiqueta })])
    );
  }
}

function renderTopbar(data) {
  const contenedor = document.getElementById("topbar-kpis");
  contenedor.innerHTML = "";
  const items = [
    ["Entrada hoy", data.entrada_hoy ?? "—"],
    ["Salida hoy", data.salida_hoy ?? "—"],
    ["Score semanal", data.score_semanal !== null ? data.score_semanal.toFixed(0) : "—"],
  ];
  for (const [etiqueta, valor] of items) {
    contenedor.appendChild(el("span", { html: `${etiqueta}: <strong>${valor}</strong>` }));
  }
}

function renderTimeline(data) {
  const contenedor = document.getElementById("timeline");
  contenedor.innerHTML = "";

  const INICIO_TRACK = 6 * 60; // 06:00
  const FIN_TRACK = 22 * 60; // 22:00
  const totalMin = FIN_TRACK - INICIO_TRACK;

  const track = el("div", { class: "timeline-track" });

  for (const pausa of data.pausas_hoy) {
    const inicio = new Date(pausa.inicio);
    const fin = pausa.fin ? new Date(pausa.fin) : new Date();
    const minInicio = inicio.getHours() * 60 + inicio.getMinutes();
    const minFin = fin.getHours() * 60 + fin.getMinutes();
    const left = Math.max(0, ((minInicio - INICIO_TRACK) / totalMin) * 100);
    const width = Math.max(0.6, ((minFin - minInicio) / totalMin) * 100);
    const color = COLOR_PAUSA[pausa.clasificacion] || COLOR_PAUSA.sin_clasificar;
    const div = el("div", {
      class: "timeline-block",
      title: `${pausa.clasificacion || "sin clasificar"} — ${pausa.duracion_min} min (${pausa.origen || "auto_inferido"})`,
    });
    div.style.left = left + "%";
    div.style.width = width + "%";
    div.style.background = color;
    track.appendChild(div);
  }

  // Marcas de entrada y salida de hoy: línea vertical sobre la barra + etiqueta.
  const marcas = el("div", { class: "timeline-marks" });
  const hitos = [
    ["Entrada", data.entrada_hoy, "var(--good)"],
    ["Salida", data.salida_hoy, "var(--accent)"],
  ];
  for (const [nombre, hora, color] of hitos) {
    if (!hora) continue;
    const [h, m] = hora.split(":").map(Number);
    const left = Math.min(100, Math.max(0, ((h * 60 + m - INICIO_TRACK) / totalMin) * 100));

    const linea = el("div", { class: "timeline-marker" });
    linea.style.left = left + "%";
    linea.style.background = color;
    track.appendChild(linea);

    const etiqueta = el("span", { class: "timeline-mark", text: `${nombre} ${hora}` });
    etiqueta.style.left = left + "%";
    etiqueta.style.color = color;
    // Evita que la etiqueta se corte en los bordes de la barra.
    etiqueta.style.transform = `translateX(${left < 12 ? "0" : left > 88 ? "-100%" : "-50%"})`;
    marcas.appendChild(etiqueta);
  }
  contenedor.appendChild(marcas);
  contenedor.appendChild(track);

  // Eje de horas con marcas de números (cada 2 horas, de 06:00 a 22:00).
  const eje = el("div", { class: "timeline-axis" });
  for (let min = INICIO_TRACK; min <= FIN_TRACK; min += 120) {
    const left = ((min - INICIO_TRACK) / totalMin) * 100;
    const hora = String(Math.floor(min / 60)).padStart(2, "0") + ":00";
    const marca = el("span", { class: "timeline-tick", text: hora });
    marca.style.left = left + "%";
    eje.appendChild(marca);
  }
  contenedor.appendChild(eje);

  if (!data.pausas_hoy.length) {
    contenedor.appendChild(el("div", { class: "empty", text: "Todavía no hay pausas registradas hoy." }));
  }

  const leyenda = el("div", { class: "timeline-legend" });
  for (const [clave, color] of Object.entries(COLOR_PAUSA)) {
    leyenda.appendChild(
      el("span", {}, [
        el("span", { class: "legend-dot", style: `background:${color}` }),
        document.createTextNode(clave.replace("_", " ")),
      ])
    );
  }
  contenedor.appendChild(leyenda);
}

function renderTendencia(data) {
  const contenedor = document.getElementById("tendencia");
  contenedor.innerHTML = "";
  const dias = data.dias.slice(-14);
  if (!dias.length) {
    contenedor.appendChild(el("div", { class: "empty", text: "Sin historial todavía." }));
    return;
  }

  const w = 480;
  const h = 150;
  const padX = 26;
  const padY = 24;
  const lienzo = svg("svg", { width: "100%", viewBox: `0 0 ${w} ${h}` });

  const yPara = (score) => h - padY - (score / 100) * (h - padY * 2);

  // Eje Y: líneas guía y marcas de números (0 / 50 / 100).
  for (const marca of [0, 50, 100]) {
    const y = yPara(marca);
    lienzo.appendChild(
      svg("line", { x1: padX, y1: y, x2: w - padX, y2: y, stroke: "var(--border)", "stroke-width": "1" })
    );
    lienzo.appendChild(svgText(padX - 6, y + 3, String(marca), { "text-anchor": "end" }));
  }

  const puntos = dias.map((d, i) => {
    const x = padX + (i / Math.max(1, dias.length - 1)) * (w - padX * 2);
    const y = yPara(d.score ?? 0);
    return [x, y, d];
  });

  const conScore = puntos.filter(([, , d]) => d.score !== null && d.score !== undefined);
  const linea = conScore.map(([x, y]) => `${x},${y}`).join(" ");
  lienzo.appendChild(svg("polyline", { points: linea, fill: "none", stroke: "var(--accent)", "stroke-width": "2" }));

  for (const [x, y, d] of puntos) {
    if (d.score === null || d.score === undefined) continue;
    const c = svg("circle", { cx: x, cy: y, r: 4, fill: colorForScore(d.score) });
    c.appendChild(el("title", { text: `${d.fecha}: ${d.score ?? "sin datos"}` }));
    lienzo.appendChild(c);
    // Marca de número: el score arriba de cada punto.
    lienzo.appendChild(
      svgText(x, y - 8, d.score.toFixed(0), { "text-anchor": "middle", fill: "var(--text)", "font-weight": "600" })
    );
  }

  contenedor.appendChild(lienzo);
}

function renderHeatmap(data) {
  const contenedor = document.getElementById("heatmap");
  contenedor.innerHTML = "";
  const grid = el("div", { class: "heatmap-grid" });
  for (const dia of data.dias) {
    const celda = el("div", { class: "heatmap-cell", title: `${dia.fecha}: ${dia.score ?? "sin datos"}` });
    celda.style.background = colorForScore(dia.score);
    grid.appendChild(celda);
  }
  contenedor.appendChild(grid);
}

function renderBarras(data) {
  const contenedor = document.getElementById("barras");
  contenedor.innerHTML = "";
  const dias = data.dias.slice(-30);
  if (!dias.length) {
    contenedor.appendChild(el("div", { class: "empty", text: "Sin historial todavía." }));
    return;
  }

  const w = Math.max(600, dias.length * 26);
  const h = 190;
  const padX = 30;
  const padTop = 22;
  const padBottom = 26; // espacio para las marcas de día abajo
  const maxHoras = Math.max(1, ...dias.map((d) => d.horas_trabajadas || 0));
  const lienzo = svg("svg", { width: "100%", viewBox: `0 0 ${w} ${h}` });

  const alturaUtil = h - padTop - padBottom;
  const yBase = h - padBottom;

  // Eje Y: líneas guía y marcas de horas (0 / mitad / máximo).
  for (const marca of [0, maxHoras / 2, maxHoras]) {
    const y = yBase - (marca / maxHoras) * alturaUtil;
    lienzo.appendChild(
      svg("line", { x1: padX, y1: y, x2: w - padX, y2: y, stroke: "var(--border)", "stroke-width": "1" })
    );
    lienzo.appendChild(svgText(padX - 6, y + 3, marca.toFixed(1) + "h", { "text-anchor": "end" }));
  }

  const paso = (w - padX * 2) / dias.length;
  const anchoBarra = paso - 6;
  dias.forEach((d, i) => {
    const horas = d.horas_trabajadas || 0;
    const alto = (horas / maxHoras) * alturaUtil;
    const x = padX + i * paso;
    const centro = x + anchoBarra / 2;
    const y = yBase - alto;
    const barra = svg("rect", {
      x,
      y,
      width: Math.max(2, anchoBarra),
      height: Math.max(1, alto),
      fill: colorForScore(d.score),
      rx: 2,
    });
    barra.appendChild(el("title", { text: `${d.fecha}: ${d.horas_trabajadas}h trabajadas` }));
    lienzo.appendChild(barra);
    // Marca de número: horas trabajadas arriba de la barra.
    if (horas > 0) {
      lienzo.appendChild(
        svgText(centro, y - 4, horas.toFixed(1), { "text-anchor": "middle", fill: "var(--text)", "font-size": 8 })
      );
    }
    // Marca de día (número del día del mes) abajo del eje.
    lienzo.appendChild(
      svgText(centro, h - 8, d.fecha.slice(-2), { "text-anchor": "middle", "font-size": 8 })
    );
  });

  contenedor.appendChild(lienzo);
}

function renderTabla(data) {
  const contenedor = document.getElementById("tabla-wrapper");
  contenedor.innerHTML = "";
  if (!data.dias.length) {
    contenedor.appendChild(el("div", { class: "empty", text: "Sin historial todavía." }));
    return;
  }

  const tabla = el("table");
  const encabezado = el("tr", {}, [
    "Fecha",
    "Entrada",
    "Salida",
    "Hs. trabajadas",
    "Hs. idle",
    "Almuerzo (min)",
    "Merienda (min)",
    "Score",
  ].map((texto) => el("th", { text: texto })));
  tabla.appendChild(encabezado);

  for (const d of [...data.dias].reverse()) {
    const badge = el("span", { class: "badge", text: d.score !== null ? d.score.toFixed(0) : "—" });
    badge.style.background = colorForScore(d.score);
    const fila = el("tr", {}, [
      el("td", { text: d.fecha }),
      el("td", { text: d.entrada || "—" }),
      el("td", { text: d.salida || "—" }),
      el("td", { text: d.horas_trabajadas ?? "—" }),
      el("td", { text: d.horas_idle ?? "—" }),
      el("td", { text: d.duracion_almuerzo_min ?? "—" }),
      el("td", { text: d.duracion_merienda_min ?? "—" }),
      el("td", {}, [badge]),
    ]);
    tabla.appendChild(fila);
  }
  contenedor.appendChild(tabla);
}

function exportarCSV(data) {
  const encabezado = ["fecha", "entrada", "salida", "horas_trabajadas", "horas_idle", "duracion_almuerzo_min", "duracion_merienda_min", "score"];
  const filas = data.dias.map((d) => encabezado.map((campo) => d[campo] ?? "").join(","));
  const csv = [encabezado.join(","), ...filas].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = el("a", { href: url, download: "control_horas.csv" });
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

window.renderDashboard = function renderDashboard(data) {
  window.__ultimoDataset = data;
  renderTopbar(data);
  renderKPIs(data);
  renderTimeline(data);
  renderTendencia(data);
  renderHeatmap(data);
  renderBarras(data);
  renderTabla(data);
};

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("exportar-csv").addEventListener("click", () => {
    if (window.__ultimoDataset) exportarCSV(window.__ultimoDataset);
  });
});
