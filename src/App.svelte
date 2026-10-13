<script lang="ts">
  import { onDestroy } from 'svelte'
  import IconCamera from '@tabler/icons-svelte-runes/icons/camera'
  import IconCheck from '@tabler/icons-svelte-runes/icons/check'
  import IconPencil from '@tabler/icons-svelte-runes/icons/pencil'
  import IconChevronLeft from '@tabler/icons-svelte-runes/icons/chevron-left'
  import IconHandClick from '@tabler/icons-svelte-runes/icons/hand-click'
  import robotCamara from './assets/robot-camara.png'
  import robotEncontrado from './assets/robot-encontrado.PNG'
  import robotOk from './assets/robot-ok.png'
  import logoRecybot from './assets/logo-recybot.png'
  import robotSaludo from './assets/robot-saludo.PNG'
  import botella from './assets/botella.PNG'
  import papelCarton from './assets/pepel.png'
  import metal from './assets/metal.png'
  import vidrio from './assets/vidrio.png'

  type Pantalla = 'bienvenida' | 'deteccion' | 'identificada' | 'categorias' | 'exito'
  type CategoriaResiduo = 'Plástico' | 'Papel / Cartón' | 'Metal' | 'Vidrio'
  type EstadoCamara = 'conectando' | 'activa' | 'error'

  const cameraStreamUrl =
    import.meta.env.VITE_CAMERA_STREAM_URL ?? 'http://127.0.0.1:8765/api/camara/stream'

  const categorias: { nombre: CategoriaResiduo; imagen: string; alt: string }[] = [
    { nombre: 'Plástico', imagen: botella, alt: 'Botella de plástico' },
    { nombre: 'Papel / Cartón', imagen: papelCarton, alt: 'Papel y cartón' },
    { nombre: 'Metal', imagen: metal, alt: 'Lata de metal' },
    { nombre: 'Vidrio', imagen: vidrio, alt: 'Botella de vidrio' },
  ]

  let pantallaActual = $state<Pantalla>('bienvenida')
  let categoriaSeleccionada = $state<CategoriaResiduo>('Plástico')
  let estadoCamara = $state<EstadoCamara>('conectando')
  let errorCamara = $state('')
  let intentoCamara = $state(0)
  let temporizadorCamara: ReturnType<typeof setTimeout> | undefined
  let imagenResiduoSeleccionado = $derived(
    categorias.find((categoria) => categoria.nombre === categoriaSeleccionada)?.imagen ?? botella,
  )

  function comenzarDeteccion() {
    pantallaActual = 'deteccion'
    conectarCamara()
  }

  function conectarCamara() {
    if (temporizadorCamara) {
      clearTimeout(temporizadorCamara)
    }

    estadoCamara = 'conectando'
    errorCamara = ''
    intentoCamara += 1
    temporizadorCamara = setTimeout(() => {
      if (estadoCamara === 'conectando') {
        estadoCamara = 'error'
        errorCamara = 'No llega video desde Recybot. Comprueba que el servicio de cámara esté iniciado.'
      }
    }, 8000)
  }

  function confirmarCamaraActiva() {
    if (temporizadorCamara) {
      clearTimeout(temporizadorCamara)
    }

    estadoCamara = 'activa'
  }

  function detenerCamara() {
    if (temporizadorCamara) {
      clearTimeout(temporizadorCamara)
      temporizadorCamara = undefined
    }
  }

  function corregirResiduo() {
    detenerCamara()
    pantallaActual = 'categorias'
  }

  function confirmarCategoria() {
    detenerCamara()
    pantallaActual = 'exito'
  }

  function volverAIdentificacion() {
    detenerCamara()
    pantallaActual = 'identificada'
  }

  function iniciarOtraClasificacion() {
    categoriaSeleccionada = 'Plástico'
    void comenzarDeteccion()
  }

  onDestroy(detenerCamara)
</script>

<svelte:head>
  <title>
    {pantallaActual === 'bienvenida'
      ? 'Bienvenida'
      : pantallaActual === 'deteccion'
        ? 'Detección'
        : pantallaActual === 'identificada'
          ? 'Residuo identificado'
          : pantallaActual === 'categorias'
            ? 'Tipo de residuo'
            : 'Clasificación confirmada'} · RecyBOT AI
  </title>
  <meta
    name="description"
    content="Acerca tu residuo a RecyBOT AI para identificarlo y clasificarlo."
  />
</svelte:head>

{#if pantallaActual === 'bienvenida'}
  <main class="pantalla-inicio relative isolate overflow-hidden bg-white text-[#080c27]">
    <button
      class="zona-tactil-inicio"
      type="button"
      aria-label="Toca la pantalla para comenzar"
      onclick={comenzarDeteccion}
    ></button>

    <section class="contenido-inicio relative z-10 flex items-center">
      <div class="bloque-texto">
        <img class="logo-recybot" src={logoRecybot} alt="RecyBOT AI" />

        <h1 class="saludo">
          <span>¡Hola!</span>
          <span class="saludo-marca">
            Soy <strong><span class="marca-recybot">RecyBOT</span><span class="marca-ai">AI</span></strong>
          </span>
        </h1>

        <div class="mensaje-principal">
          <img src={botella} alt="" class="ilustracion-botella" />
          <p>Acerca tu residuo y yo<br class="salto-escritorio" /> me encargo del resto.</p>
        </div>

        <p class="descripcion">
          Mi inteligencia artificial identificará el material y abrirá automáticamente el
          compartimento correcto.
        </p>

        <p class="indicacion-inicio" aria-hidden="true">
          <span>Toca la pantalla para comenzar</span>
          <IconHandClick class="icono-toque" size={34} stroke={2.4} />
        </p>
      </div>

      <img
        class="robot-saludando"
        src={robotSaludo}
        alt="RecyBOT AI saluda mientras reconoce una botella de plástico"
        fetchpriority="high"
        width="1322"
        height="1190"
      />
    </section>
  </main>
{:else if pantallaActual === 'deteccion'}
  <main class="pantalla-deteccion">
    <section class="composicion-deteccion" aria-label="Clasificación de residuos">
      <div class="columna-deteccion">
        <img class="logo-deteccion" src={logoRecybot} alt="RecyBOT AI" />

        <h1 class="titulo-deteccion">
          Coloca tu residuo<br />
          dentro del <span>área</span><br />
          <span>de detección</span>
        </h1>

        <p class="descripcion-deteccion">RecyBOT AI lo identificará automáticamente.</p>

        <img
          class="robot-camara"
          src={robotCamara}
          alt="RecyBOT AI te indica dónde colocar el residuo"
          width="1448"
          height="1120"
        />
      </div>

      <div class="columna-camara">
        <div
          class="vista-camara"
          role="group"
          aria-label="Vista en directo de la cámara del dispositivo"
        >
          {#if estadoCamara === 'error'}
            <div class="estado-error-camara" role="alert">
              <IconCamera size={30} stroke={2} aria-hidden="true" />
              <p>{errorCamara}</p>
              <button class="boton-reintentar-camara" type="button" onclick={conectarCamara}>
                Reintentar
              </button>
            </div>
          {:else}
            {#key intentoCamara}
              <img
                class="video-camara"
                src={cameraStreamUrl}
                alt="Vista en directo de la cámara de Recybot"
                onload={confirmarCamaraActiva}
                onerror={() => {
                  estadoCamara = 'error'
                  errorCamara = 'No se pudo conectar con la cámara de la Raspberry.'
                  if (temporizadorCamara) clearTimeout(temporizadorCamara)
                }}
              />
            {/key}
            {#if estadoCamara === 'conectando'}
              <div class="estado-cargando-camara" role="status">
                <span class="indicador-cargando-camara"></span>
                <span>Conectando con la cámara…</span>
              </div>
            {/if}
          {/if}
          <div class="marco-deteccion">
            <span class="esquina-deteccion esquina-superior-izquierda"></span>
            <span class="esquina-deteccion esquina-superior-derecha"></span>
            <span class="esquina-deteccion esquina-inferior-izquierda"></span>
            <span class="esquina-deteccion esquina-inferior-derecha"></span>
          </div>
          <div class="linea-escaneo"></div>
          <div class="estado-camara" role="status" aria-live="polite">
            <IconCamera size={20} stroke={2.2} aria-hidden="true" />
            <span class="punto-vista-previa" class:camara-activa={estadoCamara === 'activa'}></span>
            <span>{estadoCamara === 'activa' ? 'Cámara en vivo' : 'Cámara'}</span>
          </div>
        </div>

        <aside class="consejo-residuo">
          <div class="icono-consejo">
            <img src={botella} alt="" />
          </div>
          <div class="texto-consejo">
            <strong>Tip: coloca el residuo en el centro</strong>
            <p>Asegúrate de que sea visible y esté dentro del recuadro.</p>
          </div>
        </aside>
      </div>
    </section>
  </main>
{:else if pantallaActual === 'identificada'}
  <main class="pantalla-flujo pantalla-identificada">
    <img class="logo-flujo" src={logoRecybot} alt="RecyBOT AI" />

    <section class="contenido-identificada" aria-labelledby="titulo-identificada">
      <h1 id="titulo-identificada">¡Residuo <span>identificado!</span></h1>

      <div class="mensaje-identificada">
        <img src={imagenResiduoSeleccionado} alt="" />
        <p>He detectado que tu residuo<br />es de tipo <strong>{categoriaSeleccionada.toUpperCase()}.</strong></p>
      </div>

      <p class="pregunta-identificacion">¿Es correcta la identificación?</p>

      <div class="acciones-identificacion">
        <button class="boton-primario" type="button" onclick={confirmarCategoria}>
          <IconCheck size={25} stroke={3} aria-hidden="true" />
          <span>Sí, es correcto</span>
        </button>
        <button class="boton-secundario" type="button" onclick={corregirResiduo}>
          <IconPencil size={25} stroke={2.4} aria-hidden="true" />
          <span>No, corregir</span>
        </button>
      </div>
    </section>

    <img class="robot-identificacion" src={robotEncontrado} alt="RecyBOT AI señala el residuo identificado" />

  </main>
{:else if pantallaActual === 'categorias'}
  <main class="pantalla-flujo pantalla-categorias">
    <img class="logo-flujo" src={logoRecybot} alt="RecyBOT AI" />
    <button class="boton-volver" type="button" onclick={volverAIdentificacion}>
      <IconChevronLeft size={23} stroke={2.6} aria-hidden="true" />
      <span>Volver</span>
    </button>

    <section class="contenido-categorias" aria-labelledby="titulo-categorias">
      <h1 id="titulo-categorias">¿Qué <span>tipo de residuo</span> es?</h1>
      <p>Selecciona la categoría correcta:</p>

      <div class="opciones-categoria" role="group" aria-label="Categorías de residuos">
        {#each categorias as categoria (categoria.nombre)}
          <button
            class="tarjeta-categoria"
            class:seleccionada={categoriaSeleccionada === categoria.nombre}
            type="button"
            aria-pressed={categoriaSeleccionada === categoria.nombre}
            onclick={() => (categoriaSeleccionada = categoria.nombre)}
          >
            <img src={categoria.imagen} alt={categoria.alt} />
            <span>{categoria.nombre}</span>
          </button>
        {/each}
      </div>

      <button class="boton-primario boton-confirmar-categoria" type="button" onclick={confirmarCategoria}>
        <IconCheck size={25} stroke={3} aria-hidden="true" />
        <span>Confirmar selección</span>
      </button>
    </section>
  </main>
{:else}
  <main class="pantalla-flujo pantalla-exito">
    <img class="logo-flujo" src={logoRecybot} alt="RecyBOT AI" />

    <section class="contenido-exito" aria-labelledby="titulo-exito">
      <h1 id="titulo-exito">¡Perfecto!</h1>
      <div class="mensaje-exito">
        <img src={imagenResiduoSeleccionado} alt="" />
        <p>Residuo de tipo<br /><strong>{categoriaSeleccionada.toUpperCase()}</strong> confirmado.</p>
      </div>
      <p class="descripcion-exito">Ahora abriré automáticamente<br />el compartimento correspondiente.</p>
    </section>

    <img class="robot-exito" src={robotOk} alt="RecyBOT AI confirma la clasificación" />
    <button
      class="zona-reinicio"
      type="button"
      aria-label="Iniciar otra clasificación"
      onclick={iniciarOtraClasificacion}
    >
      <IconHandClick size={23} stroke={2.4} aria-hidden="true" />
      <span>Clasificar otro residuo</span>
    </button>
  </main>
{/if}
