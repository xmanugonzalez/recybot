<h1 align="center">Una forma más inteligente de separar los residuos.</h1>

<p align="center">
  RecyBOT AI es la interfaz táctil de un basurero inteligente que utiliza
  inteligencia artificial para identificar residuos y facilitar su
  correcta clasificación.
</p>

<p align="center">
  El usuario presenta un residuo, la IA identifica su material y
  permite confirmar o corregir el resultado antes de depositarlo.
</p>

<p align="center">
  <img src="docs/assets/portada.png" alt="RecyBOT AI" width="100%">
</p>

---

<h3 align="center">Tecnologías utilizadas</h3>

<p align="center">
  El proyecto combina tecnologías web modernas con inteligencia artificial para ofrecer una interfaz interactiva, rápida y sencilla de utilizar.
</p>

<p align="center">
  <img
    src="docs/assets/tecnologias.svg"
    alt="Svelte 5, TypeScript, Vite 7, Python 3.12 y YOLOv8"
  >
</p>

<br>

<h2 align="center">De la foto al material</h2>

<p align="center">
  <img
    src="docs/assets/recorrido.svg"
    alt="Flujo de clasificación inteligente: captura, análisis, selección y confirmación."
    width="100%"
  >
</p>

<br>

<p>
  <img src="docs/assets/capturar.svg" alt="Captura" width="22" height="22" align="absmiddle">
  &nbsp;<strong>01. Captura el residuo</strong>
</p>

Todo comienza con una fotografía. Desde la pantalla de bienvenida, el usuario accede a la cámara y captura el residuo que desea clasificar.

<br>

<p>
  <img src="docs/assets/clasificar.svg" alt="Clasificación" width="22" height="22" align="absmiddle">
  &nbsp;<strong>02. La inteligencia artificial hace su parte</strong>
</p>

RecyBOT AI analiza la imagen y propone una clasificación entre cuatro categorías: **Plástico, Papel / Cartón, Metal y Otros**. El sistema presenta el resultado de forma clara, facilitando la identificación del material sin necesidad de conocimientos técnicos.

<br>

<p>
  <img src="docs/assets/confirmar.svg" alt="Confirmación" width="22" height="22" align="absmiddle">
  &nbsp;<strong>03. El usuario tiene la última palabra</strong>
</p>

La inteligencia artificial propone, pero la decisión final es humana. El usuario puede **confirmar el resultado o seleccionar otro material** cuando sea necesario. Una vez confirmado, la interfaz muestra la clasificación final y permite iniciar un nuevo proceso.

<br>

<h2 align="center">La interfaz</h2>

| Bienvenida | Captura en el dispositivo |
| :---: | :---: |
| [![Pantalla de bienvenida con el robot y el botón «Toca la pantalla para comenzar».](docs/assets/bienvenida.png)](docs/assets/bienvenida.png) | [![Pantalla de captura con el área de detección y la opción de tomar una foto cuando el video directo no está disponible.](docs/assets/captura.png)](docs/assets/captura.png) |
| Un toque en la pantalla inicia el recorrido. | El marco indica dónde colocar el objeto. |

<br>

<h2 align="center">Qué hace la inteligencia artificial</h2>

RecyBOT AI utiliza YOLOv8 de Ultralytics para analizar fotografías, detectar residuos e identificar el tipo de material al que pertenecen: Plástico, Papel / Cartón, Metal u Otros.

La IA propone una clasificación que el usuario puede confirmar o corregir. Estas correcciones se almacenan para futuros entrenamientos, ayudando a mejorar progresivamente la precisión del sistema.

<br>

<h2 align="center">Arquitectura</h2>

<p align="center">
  <img
    src="docs/assets/arquitectura.png"
    alt="Diagrama de la arquitectura propuesta de RecyBOT AI, con dos Raspberry Pi, servicios de visión, un ESP32 y un panel web."
    width="100%"
  >
</p>

La **Raspberry Pi 3** captura la imagen y muestra en la pantalla táctil la categoría que el usuario puede confirmar o corregir. La **Raspberry Pi 5** clasifica el residuo con YOLOv8n. El esquema prevé que un **ESP32** accione el mecanismo de separación y reporte la posición y el nivel de llenado. El **panel web** mostraría el estado de los depósitos y las alertas.