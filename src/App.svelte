<script lang="ts">
  import { onDestroy, tick } from 'svelte'
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
  import otros from './assets/otros.png'

  type Pantalla = 'bienvenida' | 'deteccion' | 'identificada' | 'categorias' | 'exito'
  type CategoriaResiduo = 'Plástico' | 'Papel / Cartón' | 'Metal' | 'Otros'
  type ClaseResiduo = 'plastico' | 'papel_carton' | 'metal' | 'otros'
  type EstadoCamara = 'conectando' | 'activa' | 'error'
  type FuenteCamara = 'dispositivo' | 'servidor'
  type Deteccion = { clase: string; confianza: number; xyxy: number[]; categoria?: CategoriaResiduo }
  type ResultadoDeteccion = {
    detecciones: Deteccion[]
    muestra_id: string | null
    modo_modelo: 'prueba' | 'recybot'
    categoria: CategoriaResiduo | null
  }

  const cameraStreamUrl =
    import.meta.env.VITE_CAMERA_STREAM_URL ?? '/api/camara/stream'
  const fuenteCamara: FuenteCamara =
    import.meta.env.VITE_CAMERA_SOURCE === 'server' ? 'servidor' : 'dispositivo'

  const categorias: { nombre: CategoriaResiduo; clase: ClaseResiduo; imagen: string; alt: string }[] = [
    { nombre: 'Plástico', clase: 'plastico', imagen: botella, alt: 'Botella de plástico' },
    { nombre: 'Papel / Cartón', clase: 'papel_carton', imagen: papelCarton, alt: 'Papel y cartón' },
    { nombre: 'Metal', clase: 'metal', imagen: metal, alt: 'Lata de metal' },
    { nombre: 'Otros', clase: 'otros', imagen: otros, alt: 'Bolsa, vaso y taza rota como ejemplos de otros residuos' },
  ]

  let pantallaActual = $state<Pantalla>('bienvenida')
  let categoriaDetectada = $state<CategoriaResiduo | null>(null)
  let categoriaSeleccionada = $state<CategoriaResiduo | null>(null)
  let analizando = $state(false)
  let errorIA = $state('')
  let resumenIA = $state('')
  let muestraId = $state<string | null>(null)
  let guardandoConfirmacion = $state(false)
  let errorConfirmacion = $state('')
  let muestraGuardada = $state(false)
  let requiereRevisarCaja = $state(false)
  let solicitudIA: AbortController | undefined
  let estadoCamara = $state<EstadoCamara>('conectando')
  let errorCamara = $state('')
  let intentoCamara = $state(0)
  let temporizadorCamara: ReturnType<typeof setTimeout> | undefined
  let inputCamara = $state<HTMLInputElement>()
  let videoDispositivo = $state<HTMLVideoElement>()
  let streamDispositivo = $state<MediaStream>()
  let capturaManual = $state(false)
  let fotoDispositivo = $state<Blob | null>(null)
  let vistaPreviaDispositivo = $state('')
  let imagenResiduoSeleccionado = $derived(
    categorias.find((categoria) => categoria.nombre === categoriaSeleccionada)?.imagen ?? botella,
  )
  let imagenResiduoDetectado = $derived(
    categorias.find((categoria) => categoria.nombre === categoriaDetectada)?.imagen ?? botella,
  )

  function esCategoriaResiduo(valor: unknown): valor is CategoriaResiduo {
    return categorias.some((categoria) => categoria.nombre === valor)
  }

  function comenzarDeteccion() {
    errorIA = ''
    resumenIA = ''
    muestraId = null
    errorConfirmacion = ''
    muestraGuardada = false
    requiereRevisarCaja = false
    categoriaDetectada = null
    categoriaSeleccionada = null
    limpiarFotoDispositivo()
    pantallaActual = 'deteccion'
    void conectarCamara()
  }

  async function conectarCamara() {
    detenerCamara()
    if (temporizadorCamara) {
      clearTimeout(temporizadorCamara)
    }

    estadoCamara = 'conectando'
    errorCamara = ''
    capturaManual = false
    intentoCamara += 1

    if (fuenteCamara === 'dispositivo') {
      if (!navigator.mediaDevices?.getUserMedia) {
        capturaManual = true
        errorCamara = 'El navegador no permite video directo en esta dirección. Tocá para abrir la cámara del dispositivo.'
        estadoCamara = 'activa'
        return
      }
      try {
        streamDispositivo = await navigator.mediaDevices.getUserMedia({
          audio: false,
          video: { facingMode: { ideal: 'environment' } },
        })
        await tick()
        await prepararVideoDispositivo()
      } catch {
        capturaManual = true
        errorCamara = 'No se pudo abrir el video directo. Tocá para usar la cámara del dispositivo.'
        estadoCamara = 'activa'
      }
      return
    }

    temporizadorCamara = setTimeout(() => {
      if (estadoCamara === 'conectando') {
        estadoCamara = 'error'
        errorCamara = 'No llega video desde Recybot. Comprueba que el servicio de cámara esté iniciado.'
      }
    }, 8000)
  }

  async function prepararVideoDispositivo() {
    if (!videoDispositivo || !streamDispositivo) return
    videoDispositivo.srcObject = streamDispositivo
    try {
      await videoDispositivo.play()
      estadoCamara = 'activa'
    } catch {
      capturaManual = true
      errorCamara = 'No se pudo reproducir la cámara. Tocá para sacar una fotografía.'
      detenerStreamDispositivo()
      estadoCamara = 'activa'
    }
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
    detenerStreamDispositivo()
  }

  function detenerStreamDispositivo() {
    streamDispositivo?.getTracks().forEach((track) => track.stop())
    streamDispositivo = undefined
    if (videoDispositivo) videoDispositivo.srcObject = null
  }

  function limpiarFotoDispositivo() {
    fotoDispositivo = null
    if (vistaPreviaDispositivo) URL.revokeObjectURL(vistaPreviaDispositivo)
    vistaPreviaDispositivo = ''
    if (inputCamara) inputCamara.value = ''
  }

  async function convertirAJpeg(archivo: File): Promise<Blob> {
    const imagen = await createImageBitmap(archivo, { imageOrientation: 'from-image' })
    const limite = 1280
    const escala = Math.min(1, limite / Math.max(imagen.width, imagen.height))
    const canvas = document.createElement('canvas')
    canvas.width = Math.max(1, Math.round(imagen.width * escala))
    canvas.height = Math.max(1, Math.round(imagen.height * escala))
    const contexto = canvas.getContext('2d')
    if (!contexto) {
      imagen.close()
      throw new Error('No se pudo preparar la fotografía.')
    }
    contexto.drawImage(imagen, 0, 0, canvas.width, canvas.height)
    imagen.close()
    const jpeg = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.82))
    if (!jpeg) throw new Error('No se pudo convertir la fotografía.')
    return jpeg
  }

  async function capturarVideoDispositivo(): Promise<Blob> {
    if (!videoDispositivo || videoDispositivo.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
      throw new Error('La cámara todavía no está lista.')
    }
    const limite = 1280
    const escala = Math.min(1, limite / Math.max(videoDispositivo.videoWidth, videoDispositivo.videoHeight))
    const canvas = document.createElement('canvas')
    canvas.width = Math.max(1, Math.round(videoDispositivo.videoWidth * escala))
    canvas.height = Math.max(1, Math.round(videoDispositivo.videoHeight * escala))
    const contexto = canvas.getContext('2d')
    if (!contexto) throw new Error('No se pudo preparar la captura.')
    contexto.drawImage(videoDispositivo, 0, 0, canvas.width, canvas.height)
    const jpeg = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.82))
    if (!jpeg) throw new Error('No se pudo convertir la captura.')
    return jpeg
  }

  async function solicitarCaptura() {
    if (analizando || estadoCamara !== 'activa') return
    if (fuenteCamara === 'servidor') {
      await identificarResiduo()
      return
    }
    if (capturaManual) {
      inputCamara?.click()
      return
    }
    errorIA = ''
    try {
      limpiarFotoDispositivo()
      fotoDispositivo = await capturarVideoDispositivo()
      vistaPreviaDispositivo = URL.createObjectURL(fotoDispositivo)
      await identificarResiduo(fotoDispositivo)
    } catch (error) {
      errorIA = error instanceof Error ? error.message : 'No se pudo tomar la fotografía.'
    }
  }

  async function recibirFotoDispositivo(event: Event) {
    const input = event.currentTarget as HTMLInputElement
    const archivo = input.files?.[0]
    if (!archivo) return
    errorIA = ''
    try {
      limpiarFotoDispositivo()
      fotoDispositivo = await convertirAJpeg(archivo)
      vistaPreviaDispositivo = URL.createObjectURL(fotoDispositivo)
      await identificarResiduo(fotoDispositivo)
    } catch (error) {
      errorIA = error instanceof Error ? error.message : 'No se pudo preparar la fotografía.'
    }
  }

  function corregirResiduo() {
    detenerCamara()
    categoriaSeleccionada = null
    errorConfirmacion = ''
    pantallaActual = 'categorias'
  }

  async function confirmarDeteccion() {
    if (!categoriaDetectada) return
    categoriaSeleccionada = categoriaDetectada
    await confirmarCategoria()
  }

  async function confirmarCategoria() {
    if (!categoriaSeleccionada) return
    const categoria = categorias.find((item) => item.nombre === categoriaSeleccionada)
    if (!categoria) return
    guardandoConfirmacion = true
    errorConfirmacion = ''
    try {
      if (muestraId) {
        const response = await fetch('/api/muestras/confirmar', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Recybot-Review': '1',
          },
          body: JSON.stringify({ muestra_id: muestraId, clase: categoria.clase }),
        })
        const data = await response.json()
        if (!response.ok) throw new Error(data.error ?? 'No se pudo guardar la confirmación.')
        muestraGuardada = data.guardada === true
        requiereRevisarCaja = data.requiere_revisar_caja === true
      }
      detenerCamara()
      pantallaActual = 'exito'
    } catch (error) {
      errorConfirmacion = error instanceof Error
        ? error.message
        : 'No se pudo guardar la confirmación.'
    } finally {
      guardandoConfirmacion = false
    }
  }

  function mostrarIdentificacion() {
    detenerCamara()
    pantallaActual = 'identificada'
  }

  async function identificarResiduo(captura?: Blob) {
    if (analizando || estadoCamara !== 'activa') return
    analizando = true
    errorIA = ''
    solicitudIA = new AbortController()
    const timeout = setTimeout(() => solicitudIA?.abort(), 55000)
    try {
      const response = await fetch('/api/identificar', {
        method: 'POST',
        headers: captura
          ? { 'X-Recybot-Capture': '1', 'Content-Type': 'image/jpeg' }
          : { 'X-Recybot-Capture': '1' },
        body: captura,
        signal: solicitudIA.signal,
      })
      const data = await response.json() as ResultadoDeteccion & { error?: string }
      if (!response.ok) throw new Error(data.error ?? 'No se pudo analizar la imagen.')
      const nombres: Record<string, string> = {
        bottle: 'botella', person: 'persona', cup: 'taza o vaso',
        banana: 'banana', apple: 'manzana', book: 'libro', cell_phone: 'teléfono',
      }
      const detecciones = data.detecciones
      if (!Array.isArray(detecciones)) throw new Error('Respuesta de IA inválida.')
      muestraId = typeof data.muestra_id === 'string' ? data.muestra_id : null
      categoriaDetectada = esCategoriaResiduo(data.categoria)
        ? data.categoria
        : detecciones.find((deteccion) => esCategoriaResiduo(deteccion.categoria))?.categoria ?? null
      if (detecciones.length === 0) {
        resumenIA = 'No pudo reconocer el objeto. Tu confirmación ayudará a revisar este caso.'
        categoriaDetectada = null
        categoriaSeleccionada = null
        mostrarIdentificacion()
        return
      }
      if (categoriaDetectada) {
        const deteccionPrincipal = detecciones.find((deteccion) => deteccion.categoria === categoriaDetectada)
        resumenIA = deteccionPrincipal
          ? `${Math.round(deteccionPrincipal.confianza * 100)} % de confianza`
          : 'Clasificación encontrada'
      } else {
        resumenIA = detecciones.slice(0, 4).map((d) =>
          `${nombres[d.clase] ?? d.clase} (${Math.round(d.confianza * 100)} %)`
        ).join(', ')
      }
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
    detenerCamara()
    limpiarFotoDispositivo()
    errorIA = ''
    resumenIA = ''
    muestraId = null
    errorConfirmacion = ''
    muestraGuardada = false
    requiereRevisarCaja = false
    categoriaDetectada = null
    categoriaSeleccionada = null
    pantallaActual = 'bienvenida'
  }

  onDestroy(() => {
    detenerCamara()
    limpiarFotoDispositivo()
    solicitudIA?.abort()
  })
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
          {analizando
            ? 'Captura tomada · Analizando…'
            : errorIA
              ? 'Tocá el recuadro para reintentar.'
              : fuenteCamara === 'servidor'
                ? 'Tocá el video para identificar el objeto.'
                : capturaManual
                  ? 'Tocá el recuadro para sacar una foto.'
                  : 'Tocá el video para capturar el objeto.'}
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
          aria-busy={analizando}
        >
          <input
            class="entrada-camara-celular"
            bind:this={inputCamara}
            type="file"
            accept="image/*"
            capture="environment"
            aria-hidden="true"
            tabindex="-1"
            onchange={recibirFotoDispositivo}
          />
          {#if estadoCamara === 'error'}
            <div class="estado-error-camara" role="alert">
              <IconCamera size={30} stroke={2} aria-hidden="true" />
              <p>{errorCamara}</p>
              <button class="boton-reintentar-camara" type="button" onclick={conectarCamara}>
                Reintentar
              </button>
            </div>
          {:else if fuenteCamara === 'dispositivo'}
            {#if vistaPreviaDispositivo}
              <img class="video-camara" src={vistaPreviaDispositivo} alt="Fotografía tomada con este dispositivo" />
            {:else if streamDispositivo}
              <video
                class="video-camara"
                bind:this={videoDispositivo}
                muted
                playsinline
                aria-label="Vista en directo de la cámara de este dispositivo"
              ></video>
            {:else}
              <div class="estado-camara-celular">
                <IconCamera size={42} stroke={1.9} aria-hidden="true" />
                <strong>Usar cámara de este dispositivo</strong>
                <span>Tocá para sacar una sola foto</span>
                {#if errorCamara}<small role="alert">{errorCamara}</small>{/if}
              </div>
            {/if}
            <button
              class="boton-continuar-camara"
              type="button"
              aria-label={errorIA ? 'Tomar otra fotografía y reintentar el análisis' : 'Capturar con la cámara de este dispositivo'}
              disabled={analizando}
              onclick={solicitarCaptura}
            ></button>
            {#if analizando}
              <div class="estado-analisis-camara" role="status" aria-live="polite">
                <span class="indicador-cargando-camara"></span>
                <strong>Captura tomada</strong>
                <span>Analizando una sola imagen…</span>
              </div>
            {/if}
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
              aria-label={errorIA ? 'Capturar otra imagen y reintentar el análisis' : 'Capturar una imagen y analizarla'}
              disabled={analizando || estadoCamara !== 'activa'}
              onclick={() => void solicitarCaptura()}
            ></button>
            {#if analizando}
              <div class="estado-analisis-camara" role="status" aria-live="polite">
                <span class="indicador-cargando-camara"></span>
                <strong>Captura tomada</strong>
                <span>Analizando una sola imagen…</span>
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
            <span>{fuenteCamara === 'dispositivo' ? 'Cámara de este dispositivo' : estadoCamara === 'activa' ? 'Cámara de Recybot' : 'Cámara'}</span>
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
      <h1 id="titulo-identificada">
        {categoriaDetectada ? 'Residuo' : 'Resultado de'} <span>{categoriaDetectada ? 'detectado' : 'la cámara'}</span>
      </h1>

      <div class="mensaje-identificada">
        {#if categoriaDetectada}
          <img src={imagenResiduoDetectado} alt="" />
          <p>Tipo detectado:<br /><strong>{categoriaDetectada.toUpperCase()}</strong></p>
        {:else}
          <IconCamera size={48} aria-hidden="true" />
          <p>Resultado:<br /><strong>{resumenIA}</strong></p>
        {/if}
      </div>

      {#if categoriaDetectada}
        <p class="detalle-confianza">{resumenIA}</p>
        <p class="pregunta-identificacion">¿El tipo de residuo es correcto?</p>
      {:else}
        <p class="pregunta-identificacion">Elegí el material correcto para completar la clasificación.</p>
      {/if}

      {#if errorConfirmacion}<p class="error-confirmacion" role="alert">{errorConfirmacion}</p>{/if}

      <div class="acciones-identificacion">
        {#if categoriaDetectada}
          <button
            class="boton-primario"
            type="button"
            disabled={guardandoConfirmacion}
            onclick={confirmarDeteccion}
          >
            <IconCheck size={25} stroke={3} aria-hidden="true" />
            <span>{guardandoConfirmacion ? 'Guardando…' : 'Sí, es correcto'}</span>
          </button>
          <button
            class="boton-secundario"
            type="button"
            disabled={guardandoConfirmacion}
            onclick={corregirResiduo}
          >
            <IconPencil size={25} stroke={2.4} aria-hidden="true" />
            <span>Modificar tipo</span>
          </button>
        {:else}
          <button class="boton-primario" type="button" onclick={corregirResiduo}>
            <IconPencil size={25} stroke={2.4} aria-hidden="true" />
            <span>Elegir material</span>
          </button>
        {/if}
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
      <p>Al confirmar, guardaremos esta captura para revisar y mejorar el modelo.</p>

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

      {#if errorConfirmacion}<p class="error-confirmacion" role="alert">{errorConfirmacion}</p>{/if}

      <button
        class="boton-primario boton-confirmar-categoria"
        type="button"
        disabled={!categoriaSeleccionada || guardandoConfirmacion}
        onclick={confirmarCategoria}
      >
        <IconCheck size={25} stroke={3} aria-hidden="true" />
        <span>{guardandoConfirmacion ? 'Guardando…' : 'Confirmar selección'}</span>
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
      <p class="descripcion-exito">
        {muestraGuardada
          ? requiereRevisarCaja
            ? 'Captura guardada para revisar su ubicación antes del próximo entrenamiento.'
            : 'Captura y etiqueta guardadas para el próximo entrenamiento.'
          : 'Clasificación completada.'}
        <br />El mecanismo todavía no está conectado.
      </p>
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
