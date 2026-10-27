<script lang="ts">
  import { onDestroy } from 'svelte'
  import IconCamera from '@tabler/icons-svelte-runes/icons/camera'
  import IconCheck from '@tabler/icons-svelte-runes/icons/check'
  import IconPencil from '@tabler/icons-svelte-runes/icons/pencil'
  import IconChevronLeft from '@tabler/icons-svelte-runes/icons/chevron-left'
  import IconHandClick from '@tabler/icons-svelte-runes/icons/hand-click'
  import robotCamara from './assets/robot-camara.png'
  import robotEncontrado from './assets/robot-encontrado.png'
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
    import.meta.env.VITE_CAMERA_STREAM_URL ?? '/api/camara/stream'

  const categorias: { nombre: CategoriaResiduo; imagen: string; alt: string }[] = [
    { nombre: 'Plástico', imagen: botella, alt: 'Botella de plástico' },
    { nombre: 'Papel / Cartón', imagen: papelCarton, alt: 'Papel y cartón' },
    { nombre: 'Metal', imagen: metal, alt: 'Lata de metal' },
    { nombre: 'Vidrio', imagen: vidrio, alt: 'Botella de vidrio' },
  ]

  let pantallaActual = $state<Pantalla>('bienvenida')
  let categoriaSeleccionada = $state<CategoriaResiduo | null>(null)
  let analizando = $state(false)
  let errorIA = $state('')
  let resumenIA = $state('')
  let solicitudIA: AbortController | undefined
  let estadoCamara = $state<EstadoCamara>('conectando')
  let errorCamara = $state('')
  let intentoCamara = $state(0)
  let temporizadorCamara: ReturnType<typeof setTimeout> | undefined
  let imagenResiduoSeleccionado = $derived(
    categorias.find((categoria) => categoria.nombre === categoriaSeleccionada)?.imagen ?? botella,
  )

  function comenzarDeteccion() {
    errorIA = ''
    resumenIA = ''
    categoriaSeleccionada = null
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
    if (!categoriaSeleccionada) return
    detenerCamara()
    pantallaActual = 'exito'
  }

  function mostrarIdentificacion() {
    detenerCamara()
    pantallaActual = 'identificada'
  }

  async function identificarResiduo() {
    if (analizando) return
    analizando = true
    errorIA = ''
    solicitudIA = new AbortController()
    const timeout = setTimeout(() => solicitudIA?.abort(), 55000)
    try {
      const response = await fetch('/api/identificar', {
        method: 'POST',
        headers: { 'X-Recybot-Capture': '1' },
        signal: solicitudIA.signal,
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error ?? 'No se pudo analizar la imagen.')
      const nombres: Record<string, string> = {
        bottle: 'botella', person: 'persona', cup: 'taza o vaso',
        banana: 'banana', apple: 'manzana', book: 'libro', cell_phone: 'teléfono',
      }
      const detecciones = data.detecciones as { clase: string; confianza: number }[]
      if (!Array.isArray(detecciones)) throw new Error('Respuesta de IA inválida.')
      if (detecciones.length === 0) {
        errorIA = 'No se detectó un objeto. Acercalo al centro, mejorá la iluminación y tocá el video para reintentar.'
        return
      }
      resumenIA = detecciones.slice(0, 4).map((d) =>
        `${nombres[d.clase] ?? d.clase} (${Math.round(d.confianza * 100)} %)`
      ).join(', ')
      categoriaSeleccionada = null
      mostrarIdentificacion()
    } catch (error) {
      errorIA = error instanceof Error && error.name !== 'AbortError'
        ? error.message : 'La identificación tardó demasiado. Volvé a intentar.'
    } finally {
      clearTimeout(timeout)
      solicitudIA = undefined
      analizando = false
    }
  }

  function iniciarOtraClasificacion() {
    categoriaSeleccionada = null
    void comenzarDeteccion()
  }

  onDestroy(() => { detenerCamara(); solicitudIA?.abort() })
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
          Reconozco objetos con la cámara. Confirmá el material para completar esta prueba.
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

        <p class="descripcion-deteccion" aria-live="polite">
          {analizando ? 'Analizando la captura en la Pi 5…' : 'Tocá el video para identificar el objeto.'}
        </p>
        {#if errorIA}<p role="alert">{errorIA}</p>{/if}

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
            <button
              class="boton-continuar-camara"
              type="button"
              aria-label="Capturar imagen y analizar en la Pi 5"
              disabled={analizando}
              onclick={identificarResiduo}
            ></button>
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
      <h1 id="titulo-identificada">Resultado de <span>la cámara</span></h1>

      <div class="mensaje-identificada">
        <IconCamera size={48} aria-hidden="true" />
        <p>La Pi 5 detectó:<br /><strong>{resumenIA}</strong></p>
      </div>

      <p class="pregunta-identificacion">YOLOv8n reconoce objetos, pero no confirma su material.</p>

      <div class="acciones-identificacion">
        <button class="boton-primario" type="button" onclick={corregirResiduo}>
          <IconCheck size={25} stroke={3} aria-hidden="true" />
          <span>Elegir material</span>
        </button>
        <button class="boton-secundario" type="button" onclick={comenzarDeteccion}>
          <IconPencil size={25} stroke={2.4} aria-hidden="true" />
          <span>Repetir captura</span>
        </button>
      </div>
    </section>

    <img class="robot-identificacion" src={robotEncontrado} alt="RecyBOT AI señala el residuo identificado" />

  </main>
{:else if pantallaActual === 'categorias'}
  <main class="pantalla-flujo pantalla-categorias">
    <img class="logo-flujo" src={logoRecybot} alt="RecyBOT AI" />
    <button class="boton-volver" type="button" onclick={mostrarIdentificacion}>
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

      <button class="boton-primario boton-confirmar-categoria" type="button" disabled={!categoriaSeleccionada} onclick={confirmarCategoria}>
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
        <p>Residuo de tipo<br /><strong>{categoriaSeleccionada?.toUpperCase()}</strong> confirmado por vos.</p>
      </div>
      <p class="descripcion-exito">Prueba completada.<br />El mecanismo todavía no está conectado.</p>
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
