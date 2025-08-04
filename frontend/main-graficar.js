const BACKEND_URL = "http://localhost:5000";
const listaArchivos = document.getElementById("lista-archivos");
const contenedorGraficos = document.getElementById("contenedor-graficos");

// Cargar archivos graficables
async function cargarArchivosGraficables() {
  const res = await fetch(`${BACKEND_URL}/documentos`, {
    credentials: "include"
  });
  const documentos = await res.json();

  const graficables = documentos.filter(doc => ['xlsx', 'csv'].includes(doc.tipo.toLowerCase()));
  listaArchivos.innerHTML = "";

  for (const doc of graficables) {
    const div = document.createElement("div");
    div.className = "archivo";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.name = "archivo";
    checkbox.value = doc.id;

    const label = document.createElement("label");
    label.textContent = `${doc.categoria} - ${doc.nombre}`;

    div.appendChild(checkbox);
    div.appendChild(label);

    // Contenedor para hojas
    const hojasDiv = document.createElement("div");
    hojasDiv.className = "hojas";
    hojasDiv.id = `hojas-${doc.id}`;
    div.appendChild(hojasDiv);

    listaArchivos.appendChild(div);

    // Cargar hojas/columnas
    const hojasRes = await fetch(`${BACKEND_URL}/api/hojas/${doc.id}`, {
      credentials: "include"
    });
    const hojas = await hojasRes.json();

    hojas.forEach(nombre => {
      const hojaCheckbox = document.createElement("input");
      hojaCheckbox.type = "checkbox";
      hojaCheckbox.name = `hoja-${doc.id}`;
      hojaCheckbox.value = nombre;

      const hojaLabel = document.createElement("label");
      hojaLabel.textContent = nombre;

      hojasDiv.appendChild(hojaCheckbox);
      hojasDiv.appendChild(hojaLabel);
      hojasDiv.appendChild(document.createElement("br"));
    });
  }
}

// Enviar selección y graficar
document.getElementById("generarGraficos").addEventListener("click", async () => {
  const seleccion = [];

  document.querySelectorAll("input[name='archivo']:checked").forEach(cb => {
    const id = cb.value;
    const hojas = Array.from(document.querySelectorAll(`input[name='hoja-${id}']:checked`))
      .map(h => h.value);
    if (hojas.length > 0) {
      seleccion.push({ id: parseInt(id), hojas });
    }
  });

  if (seleccion.length === 0) {
    alert("Selecciona al menos un archivo y una hoja.");
    return;
  }

  const res = await fetch(`${BACKEND_URL}/api/graficos-multiples`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(seleccion),
    credentials: "include"
  });

  const datos = await res.json();
  contenedorGraficos.innerHTML = "";

  Object.entries(datos).forEach(([nombreArchivo, registros], index) => {
    const claves = Object.keys(registros[0] || {});
    if (claves.length < 2) return;

    const etiquetas = registros.map(r => r[claves[0]]);
    const valores = registros.map(r => parseFloat(r[claves[1]]) || 0);

    const canvas = document.createElement("canvas");
    canvas.id = `grafico-${index}`;
    contenedorGraficos.appendChild(canvas);

    new Chart(canvas, {
      type: 'bar',
      data: {
        labels: etiquetas,
        datasets: [{
          label: nombreArchivo,
          data: valores,
          backgroundColor: 'rgba(75, 192, 192, 0.5)',
          borderColor: 'rgba(75, 192, 192, 1)',
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        scales: {
          y: { beginAtZero: true }
        }
      }
    });
  });
});

// Inicializar
cargarArchivosGraficables();
