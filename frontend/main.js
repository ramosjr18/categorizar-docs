// === CONFIGURACIÓN GLOBAL ===
const API_BASE_URL = "http://localhost:5000"; // 🔹 Cambia aquí si el backend está en otro host/puerto

const contenedor = document.getElementById("contenedorCategorias");
const filtro = document.getElementById("filtroCategoria");

let timeoutMensaje;

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
              ? `<button onclick="window.open('inventario.html?id=${doc.id}', '_blank')">Graficar</button>`
              : `<button onclick="window.open('ip-graficos.html?id=${doc.id}', '_blank')">Graficar</button>`;
          }
        }

        if (!esXlsxOCsv) {
          if (esDocx) {
            botonVer = `<button onclick="window.open('${API_BASE_URL}/ver_docx?nombre=${doc.nombre}', '_blank')">Ver</button>`;
          } else {
            botonVer = `<button onclick="window.open('preview.html?nombre=${doc.nombre}', '_blank')">Ver</button>`;
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

// --- Subida múltiple ---
document.getElementById("uploadForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const archivos = e.target.archivo.files;
  if (!archivos.length) {
    mostrarMensaje("⚠️ Debes seleccionar al menos un archivo.", "error");
    return;
  }

  const formData = new FormData();
  for (let file of archivos) {
    formData.append("archivo", file);
  }

  try {
    const res = await fetch(`${API_BASE_URL}/upload`, {
      method: "POST",
      body: formData,
      credentials: 'include'
    });

    const data = await res.json();

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
