// === CONFIGURACIÓN GLOBAL ===
const API_BASE_URL = "http://localhost:5000"; // Cambia si tu backend está en otro host/puerto
const API_BASE_URL_8000 = "http://localhost:8000";

const contenedor = document.getElementById("contenedorCategorias");
const filtro = document.getElementById("filtroCategoria");

let timeoutMensaje;

// Guardamos selección de archivos para poder reintentar con estrategia
window.__archivosSeleccionados = [];

// Extensiones permitidas (solo estas)
const EXT_PERMITIDAS = ["pdf", "xlsx", "docx", "csv"];

// ============ Utilidades base ============
function mostrarMensaje(texto, tipo = "error", duracion = 10000) {
  const mensaje = document.getElementById("mensaje");

  const cerrar = document.createElement("span");
  cerrar.textContent = "✖";
  cerrar.style.float = "right";
  cerrar.style.cursor = "pointer";
  cerrar.style.marginLeft = "10px";
  cerrar.onclick = () => {
    mensaje.textContent = "";
    mensaje.className = "mensaje";
  };

  mensaje.innerHTML = texto;
  mensaje.appendChild(cerrar);
  mensaje.className = "mensaje " + tipo;

  clearTimeout(timeoutMensaje);
  timeoutMensaje = setTimeout(() => {
    mensaje.textContent = "";
    mensaje.className = "mensaje";
  }, duracion);
}

function ext(name) {
  return String(name || "").toLowerCase().split(".").pop();
}

function esPermitido(file) {
  return EXT_PERMITIDAS.includes(ext(file.name));
}

function filtrarArchivos(archivosLike) {
  const arr = Array.from(archivosLike || []);
  const permitidos = arr.filter(esPermitido);
  const rechazados = arr.filter(f => !esPermitido(f));
  if (rechazados.length) {
    const lista = rechazados.map(f => f.name).slice(0, 5).join(", ");
    mostrarMensaje(`⚠️ Se omiten archivos no permitidos: ${lista}${rechazados.length > 5 ? "…" : ""}`, "error", 7000);
  }
  return permitidos;
}

function aproximarNombre(nombre) {
  return String(nombre || "")
    .toLowerCase()
    .replace(/\s+/g, "_")
    .replace(/[^a-z0-9_.-]/g, "");
}

function buscarFilePorNombreServidor(nombreServidor) {
  const lista = window.__archivosSeleccionados || [];
  // 1) Exacto
  let f = lista.find(f => f.name === nombreServidor);
  if (f) return f;
  // 2) Normalizado
  const normServ = aproximarNombre(nombreServidor);
  f = lista.find(ff => aproximarNombre(ff.name) === normServ);
  if (f) return f;
  // 3) Basename
  const baseServ = nombreServidor.split("/").pop();
  f = lista.find(ff => aproximarNombre(ff.name.split("/").pop()) === aproximarNombre(baseServ));
  return f || null;
}

// ============ Modal de DECISIÓN (409) ============
const modalDecision = document.getElementById("modalDecision");
const decisionNombre = document.getElementById("decisionNombre");
const decisionVersion = document.getElementById("decisionVersion");
const decisionMensaje = document.getElementById("decisionMensaje");
const decisionDiffText = document.getElementById("decisionDiffText");
const decisionDiffBar = document.getElementById("decisionDiffBar");

const btnReplace = document.getElementById("btnReplace");
const btnNewVersion = document.getElementById("btnNewVersion");
const btnOmitir = document.getElementById("btnOmitir");

let __onKeyDownHandler = null;

// Intenta extraer "12.34%" desde textos como "Cambio detectado de 12.34% respecto a v3"
function parseDiffPercent(texto) {
  const m = String(texto || "").match(/(\d+(?:\.\d+)?)\s*%/);
  const p = m ? parseFloat(m[1]) : NaN;
  return Number.isFinite(p) ? Math.max(0, Math.min(100, p)) : null;
}

function abrirModalDecision({ nombre, version, mensaje, diffPercent }) {
  decisionNombre.textContent = nombre || "";
  decisionVersion.textContent = version != null ? version : "?";
  decisionMensaje.textContent = mensaje || "";

  const p = diffPercent != null ? diffPercent : parseDiffPercent(mensaje);
  const pctText = p != null ? `${p.toFixed(2)}%` : "—";
  decisionDiffText.textContent = pctText;
  decisionDiffBar.style.width = p != null ? `${p}%` : "0%";

  // Color según magnitud del cambio
  if (p == null) {
    decisionDiffBar.style.background = "#888";
  } else if (p < 1) {
    decisionDiffBar.style.background = "#27ae60"; // verde (cambio bajo)
  } else if (p < 10) {
    decisionDiffBar.style.background = "#f1c40f"; // amarillo
  } else {
    decisionDiffBar.style.background = "#e67e22"; // anaranjado/alto
  }

  modalDecision.classList.add("show");
  modalDecision.setAttribute("aria-hidden", "false");

  // Atajos de teclado: R / N / Esc / Enter
  __onKeyDownHandler = (ev) => {
    const k = ev.key.toLowerCase();
    if (k === "escape") { btnOmitir.click(); }
    else if (k === "r") { btnReplace.click(); }
    else if (k === "n") { btnNewVersion.click(); }
    else if (k === "enter") { btnNewVersion.click(); } // por defecto: nueva versión
  };
  document.addEventListener("keydown", __onKeyDownHandler);
}

function cerrarModalDecision() {
  modalDecision.classList.remove("show");
  modalDecision.setAttribute("aria-hidden", "true");
  if (__onKeyDownHandler) {
    document.removeEventListener("keydown", __onKeyDownHandler);
    __onKeyDownHandler = null;
  }
}

/**
 * Muestra modal y resuelve con "replace" | "new_version" | null (si omite)
 */
function pedirDecisionModal(item) {
  return new Promise((resolve) => {
    const nombre = item?.nombre || "";
    const version = item?.version_actual ?? "?";
    const mensaje = item?.mensaje || "";

    abrirModalDecision({
      nombre,
      version,
      mensaje,
      diffPercent: parseDiffPercent(mensaje)
    });

    const onReplace = () => { limpiar(); resolve("replace"); };
    const onNewVersion = () => { limpiar(); resolve("new_version"); };
    const onOmitir = () => { limpiar(); resolve(null); };

    function limpiar() {
      btnReplace.removeEventListener("click", onReplace);
      btnNewVersion.removeEventListener("click", onNewVersion);
      btnOmitir.removeEventListener("click", onOmitir);
      cerrarModalDecision();
    }

    btnReplace.addEventListener("click", onReplace);
    btnNewVersion.addEventListener("click", onNewVersion);
    btnOmitir.addEventListener("click", onOmitir);
  });
}

// ============ Lógica de reintento/409 ============
async function reenviarConEstrategia(file, estrategia) {
  const form = new FormData();
  form.append("archivo", file);
  form.append("estrategia", estrategia);

  const res = await fetch(`${API_BASE_URL}/upload`, {
    method: "POST",
    body: form,
    credentials: "include",
  });

  const data = await res.json().catch(() => ({}));

  if (res.status === 409) {
    // Vuelve a requerir decisión por algún motivo extraño
    const conflictos = (Array.isArray(data) ? data : []).filter(x => x.requires_decision);
    for (const c of conflictos) {
      const eleccion = await pedirDecisionModal(c);
      if (!eleccion) {
        mostrarMensaje(`⏭️ Omitido: ${c.nombre}`, "error");
        continue;
      }
      const file2 = buscarFilePorNombreServidor(c.nombre);
      if (!file2) {
        mostrarMensaje(`❌ No se encontró el archivo local para reintentar: ${c.nombre}`, "error");
        continue;
      }
      await reenviarConEstrategia(file2, eleccion);
    }
    return;
  }

  if (!res.ok) {
    const mensajeError = data.error || "❌ Error aplicando estrategia al archivo.";
    mostrarMensaje(mensajeError, "error");
    console.error("Reintento con estrategia falló:", data);
    return;
  }

  // Éxito
  const msg = Array.isArray(data) ? (data[0]?.mensaje || "Procesado con éxito.") : (data.mensaje || "Procesado con éxito.");
  mostrarMensaje(`✅ ${file.name}: ${msg}`, "exito", 6000);
}

async function manejarConflictosYReenviar(resultados) {
  const conflictos = resultados.filter(r => r && r.requires_decision);
  const otros = resultados.filter(r => r && !r.requires_decision);

  // Mostrar feedback de no-conflictos
  for (const item of otros) {
    if (item.error) {
      mostrarMensaje(`❌ ${item.nombre || ""}: ${item.error}`, "error");
    } else if (item.mensaje) {
      mostrarMensaje(`✅ ${item.nombre_visible || item.nombre || ""}: ${item.mensaje}`, "exito", 6000);
    }
  }

  // Resolver conflictos uno por uno con modal
  for (const item of conflictos) {
    const file = buscarFilePorNombreServidor(item.nombre);
    if (!file) {
      mostrarMensaje(`❌ No se encontró el archivo local para decidir: ${item.nombre}`, "error");
      continue;
    }
    const eleccion = await pedirDecisionModal(item);
    if (!eleccion) {
      mostrarMensaje(`⏭️ Omitido: ${item.nombre}`, "error");
      continue;
    }
    await reenviarConEstrategia(file, eleccion);
  }

  // Refrescar lista al final
  await cargarDocumentos(filtro.value);
}

// ============ Resto de utilidades existentes ============
function obtenerNombrePersonalizado(doc) {
  switch (doc.categoria) {
    case "General": return `📄 ${doc.nombre}`;
    case "Inventario": return `📦 ${doc.nombre}`;
    case "Reporte": return `📊 ${doc.nombre}`;
    case "Sistemas y Servidores": return `🖥️ ${doc.nombre}`;
    case "Finanzas": return `💰 ${doc.nombre}`;
    case "Legal": return `📚 ${doc.nombre}`;
    case "Politicas y Controles": return `🔐 ${doc.nombre}`;
    default: return doc.nombre;
  }
}

async function fetchArchivoParaValidar(doc) {
  try {
    const url = `${API_BASE_URL}/documentos/${doc.id}/descargar`;
    const res = await fetch(url, { credentials: 'include' });
    if (!res.ok) throw new Error('No se pudo descargar archivo');
    const blob = await res.blob();
    const formData = new FormData();
    formData.append('archivo', blob, doc.nombre);
    return formData;
  } catch (error) {
    console.error("Error descargando archivo para validar:", error);
    throw error;
  }
}

async function esArchivoGraficable(doc) {
  const extension = doc.nombre.toLowerCase().split('.').pop();
  if (!['xlsx', 'csv'].includes(extension)) return false;

  try {
    const formData = await fetchArchivoParaValidar(doc);
    const response = await fetch(`${API_BASE_URL}/validar_graficable`, {
      method: 'POST',
      body: formData,
      credentials: 'include'
    });
    if (!response.ok) {
      console.error("Error en respuesta de validar_graficable:", await response.text());
      return false;
    }
    const data = await response.json();
    return data.graficable === true;
  } catch (err) {
    console.error('Error validando archivo graficable:', err);
    return false;
  }
}

async function cargarDocumentos(categoria = "todas") {
  try {
    const res = await fetch(`${API_BASE_URL}/documentos`, {
      credentials: 'include'
    });
    if (!res.ok) throw new Error("Error al obtener documentos");

    const docs = await res.json();
    contenedor.innerHTML = "";

    const agrupados = {};
    for (const doc of docs) {
      if (categoria !== "todas" && doc.categoria !== categoria) continue;
      if (!agrupados[doc.categoria]) agrupados[doc.categoria] = [];
      agrupados[doc.categoria].push(doc);
    }

    if (Object.keys(agrupados).length === 0) {
      contenedor.innerHTML = "<p>No hay documentos para esta categoría.</p>";
      return;
    }

    for (const [categoria, documentos] of Object.entries(agrupados)) {
      const categoriaDiv = document.createElement("div");
      categoriaDiv.className = "categorias";

      const nombreCategoria = document.createElement("div");
      nombreCategoria.className = "nombre-categoria";
      nombreCategoria.textContent = categoria;
      categoriaDiv.appendChild(nombreCategoria);

      const lista = document.createElement("ul");

      for (const doc of documentos) {
        const item = document.createElement("li");
        const nombrePersonalizado = obtenerNombrePersonalizado(doc);

        const extension = doc.nombre.toLowerCase().split('.').pop();
        const esDocx = extension === 'docx';
        const esXlsxOCsv = ['xlsx', 'csv'].includes(extension);
        const esInventario = doc.categoria === 'Inventario';

        let botonGraficar = '';
        let botonDetalle = '';
        let botonVer = '';

        if (esXlsxOCsv) {
          botonDetalle = `<button onclick="window.open('detalle.html?id=${doc.id}', '_blank')">Ver</button>`;
        }

        let esArchivoRealmenteGraficable = false;
        if (esXlsxOCsv) {
          esArchivoRealmenteGraficable = await esArchivoGraficable(doc);
          if (esArchivoRealmenteGraficable) {
            botonGraficar = esInventario
              ? `<button onclick="window.open('${API_BASE_URL_8000}/inventario.html?id=${doc.id}', '_blank')">Graficar</button>`
              : `<button onclick="window.open('${API_BASE_URL_8000}/ip-graficos.html?id=${doc.id}', '_blank')">Graficar</button>`;
          }
        }

        if (!esXlsxOCsv) {
          if (esDocx) {
            botonVer = `<button onclick="window.open('${API_BASE_URL}/ver_docx?nombre=${encodeURIComponent(doc.nombre)}', '_blank')">Ver</button">`;
          } else {
            botonVer = `<button onclick="window.open('${API_BASE_URL_8000}/preview.html?nombre=${encodeURIComponent(doc.nombre)}', '_blank')">Ver</button>`;
          }
        }

        const botonDescargar = `<button onclick="window.open('${API_BASE_URL}/documentos/${doc.id}/descargar', '_blank')">Descargar</button>`;

        item.innerHTML = `
          ${nombrePersonalizado}
          ${botonDetalle}
          ${botonVer}
          <button onclick="eliminar('${doc.id}')">Eliminar</button>
          ${botonGraficar}
          ${botonDescargar}
        `;
        lista.appendChild(item);
      }

      categoriaDiv.appendChild(lista);
      contenedor.appendChild(categoriaDiv);
    }
  } catch (error) {
    mostrarMensaje("❌ Error al cargar documentos.", "error");
    console.error("Error cargando documentos:", error);
  }
}

async function eliminar(id) {
  try {
    const res = await fetch(`${API_BASE_URL}/documentos/${id}`, {
      method: "DELETE",
      credentials: 'include'
    });
    if (!res.ok) throw new Error("No se pudo eliminar");

    mostrarMensaje("🧹 Documento eliminado", "exito");
    cargarDocumentos(filtro.value);
  } catch (err) {
    mostrarMensaje("❌ Error al eliminar el documento.", "error");
    console.error(err);
  }
}

// --- Buscador ---
document.getElementById("buscadorDocumentos").addEventListener("input", function () {
  const textoBusqueda = this.value.toLowerCase();
  const items = document.querySelectorAll("#contenedorCategorias li");

  items.forEach(item => {
    const nombre = item.textContent.toLowerCase();
    item.style.display = nombre.includes(textoBusqueda) ? "" : "none";
  });

  const categorias = document.querySelectorAll(".categorias");
  categorias.forEach(cat => {
    const visibles = cat.querySelectorAll("li:not([style*='display: none'])");
    cat.style.display = visibles.length > 0 ? "" : "none";
  });
});

// --- Subida múltiple desde ARCHIVOS ---
document.getElementById("uploadForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = e.target.querySelector('#archivo');
  let archivos = filtrarArchivos(input.files);
  if (!archivos.length) {
    mostrarMensaje("⚠️ Debes seleccionar al menos un archivo permitido (.pdf, .xlsx, .docx, .csv).", "error");
    return;
  }

  window.__archivosSeleccionados = archivos;

  const formData = new FormData();
  for (let file of archivos) formData.append("archivo", file);

  try {
    const res = await fetch(`${API_BASE_URL}/upload`, {
      method: "POST",
      body: formData,
      credentials: 'include'
    });

    const data = await res.json();

    if (res.status === 409 && Array.isArray(data)) {
      await manejarConflictosYReenviar(data);
      return;
    }

    if (!res.ok) {
      const mensajeError = data.error || "❌ No se pudo subir el archivo.";
      mostrarMensaje(`❌ ${mensajeError}`, "error");
      return;
    }

    mostrarMensaje("✅ Archivo(s) subido(s) correctamente", "exito");
    cargarDocumentos(filtro.value);

  } catch (err) {
    mostrarMensaje("❌ No se pudo subir el archivo. Intenta nuevamente.", "error");
    console.error(err);
  }
});

// --- Subida múltiple desde CARPETA ---
document.getElementById("uploadFolderForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const carpetaInput = document.getElementById('carpeta');
  let archivos = filtrarArchivos(carpetaInput.files);
  if (!archivos.length) {
    mostrarMensaje("⚠️ La carpeta no contiene archivos permitidos (.pdf, .xlsx, .docx, .csv).", "error");
    return;
  }

  window.__archivosSeleccionados = archivos;

  const form = new FormData();
  for (const f of archivos) form.append('archivo', f);

  try {
    const res = await fetch(`${API_BASE_URL}/upload`, {
      method: 'POST',
      body: form,
      credentials: 'include'
    });
    const data = await res.json().catch(() => ({}));

    if (res.status === 409 && Array.isArray(data)) {
      await manejarConflictosYReenviar(data);
      return;
    } else if (!res.ok) {
      mostrarMensaje(data.error || "❌ Error subiendo carpeta.", "error");
    } else {
      mostrarMensaje("✅ Carpeta subida", "exito");
      cargarDocumentos(filtro.value);
    }
  } catch (err) {
    mostrarMensaje("❌ No se pudo subir la carpeta. Intenta nuevamente.", "error");
    console.error(err);
  }
});

document.getElementById("aplicarFiltro").addEventListener("click", () => {
  const categoria = filtro.value;
  cargarDocumentos(categoria);
});

// --- Verificar sesión ---
async function verificarSesion() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/check-session`, { credentials: 'include' });
    if (!res.ok) {
      window.location.href = '/login.html';
      return false;
    }
    return true;
  } catch (error) {
    window.location.href = '/login.html';
    return false;
  }
}

verificarSesion().then(estaLogueado => {
  if (estaLogueado) {
    cargarDocumentos();
  }
});

// --- Opcional: evitar error si se llama toggleModal() desde el HTML del modal de progreso ---
function toggleModal() {
  const modal = document.getElementById('modalProgreso');
  if (!modal) return;
  modal.classList.toggle('show');
}
