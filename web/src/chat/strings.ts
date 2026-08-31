/**
 * The widget's chrome copy, verbatim from the design artboard (docs/design/DESIGN-BRIEF.md §2.5).
 *
 * The EN/ES toggle swaps chrome only. The Assistant's own answers follow the Visitor's language
 * because the system prompt says so — the toggle never asks the model for a translation, and
 * messages already on screen are not retranslated.
 */

export type Language = 'en' | 'es'

export interface QuickReply {
  id: string
  label: string
}

export interface Chrome {
  headerTitle: string
  presenceOnline: string
  presenceOffline: string
  placeholder: string
  greeting: string
  quickReplies: QuickReply[]
  openChat: string
  closeChat: string
  expand: string
  collapse: string
  send: string
  language: string
  typing: string
  nextStep: string
  connectionError: string
  /** The Hand-over offer card, and what it says once the Visitor has answered it. */
  offerPrompt: string
  offerYes: string
  offerKeepChatting: string
  offerAccepted: string
  offerDeclined: string
  /** The Assistant's own lines after an answer — `NoteKey` in `types.ts`. */
  handoverDeclined: string
  handoverConnecting: string
  /** The "Your details" card. */
  detailsTitle: string
  detailsName: string
  detailsEmail: string
  detailsCompany: string
  detailsSubmit: string
  detailsDone: string
  detailsFailed: string
  /** The Callback confirmation. */
  callbackTitle: string
  callbackBody: string
}

const EN: Chrome = {
  headerTitle: 'Cadre AI Assistant',
  presenceOnline: 'A strategist is online',
  presenceOffline: 'Strategists are offline — we still reply instantly',
  placeholder: 'Ask about services, industries, pricing…',
  greeting:
    "Hi there — I'm Cadre's AI assistant. I answer from what Cadre publishes, with a " +
    'citation for every claim. What can I help with?',
  quickReplies: [
    { id: 'services', label: 'What does Cadre AI do?' },
    { id: 'pricing', label: 'What does it cost?' },
    { id: 'portal', label: 'Where do I see my agents’ results?' },
    { id: 'strategist', label: 'Talk to a strategist' },
  ],
  openChat: 'Open the Cadre AI Assistant',
  closeChat: 'Close',
  expand: 'Expand',
  collapse: 'Shrink',
  send: 'Send',
  language: 'Language',
  typing: 'The Assistant is typing',
  nextStep: 'Next step:',
  connectionError:
    'I lost the connection before I could answer. Please try again — or reach the team at ' +
    'hello@gocadre.ai or (619) 324-3223.',
  offerPrompt: 'Do you want to jump into a call with our experts?',
  offerYes: 'Yes',
  offerKeepChatting: 'Keep chatting',
  offerAccepted: 'Connecting…',
  offerDeclined: 'No problem — offer stays open on our side.',
  handoverDeclined:
    "No problem — I'm right here if you change your mind. What else can I help with?",
  handoverConnecting: 'Connecting you with a strategist…',
  detailsTitle: 'Your details',
  detailsName: 'Full name',
  detailsEmail: 'Work email',
  detailsCompany: 'Company',
  detailsSubmit: 'Share details',
  detailsDone: '✓ Details shared with the strategist',
  detailsFailed: 'I could not save those details. Please try again.',
  callbackTitle: 'A strategist will call you back',
  callbackBody:
    "No strategist can join right now, so I've logged a callback with your details. Someone " +
    'from Cadre will reach out.',
}

const ES: Chrome = {
  headerTitle: 'Asistente de Cadre AI',
  presenceOnline: 'Hay un estratega en línea',
  presenceOffline: 'Estrategas fuera de línea — respondemos al instante',
  placeholder: 'Pregunta sobre servicios, industrias, precios…',
  greeting:
    'Hola — soy el asistente de Cadre AI. Respondo con base en lo que Cadre publica, ' +
    'citando cada afirmación. ¿En qué te ayudo?',
  quickReplies: [
    { id: 'services', label: '¿Qué hace Cadre AI?' },
    { id: 'pricing', label: '¿Cuánto cuesta?' },
    { id: 'portal', label: '¿Dónde veo los resultados de mis agentes?' },
    { id: 'strategist', label: 'Hablar con un estratega' },
  ],
  openChat: 'Abrir el asistente de Cadre AI',
  closeChat: 'Cerrar',
  expand: 'Expandir',
  collapse: 'Reducir',
  send: 'Enviar',
  language: 'Idioma',
  typing: 'El asistente está escribiendo',
  nextStep: 'Siguiente paso:',
  connectionError:
    'Perdí la conexión antes de poder responder. Inténtalo de nuevo — o escribe a ' +
    'hello@gocadre.ai o llama al (619) 324-3223.',
  offerPrompt: '¿Quieres entrar en una llamada con nuestros expertos?',
  offerYes: 'Sí',
  offerKeepChatting: 'Seguir conversando',
  offerAccepted: 'Conectando…',
  offerDeclined: 'Sin problema — la oferta sigue abierta de nuestro lado.',
  handoverDeclined:
    'Sin problema — aquí sigo si cambias de opinión. ¿En qué más te puedo ayudar?',
  handoverConnecting: 'Te estoy conectando con un estratega…',
  detailsTitle: 'Tus datos',
  detailsName: 'Nombre completo',
  detailsEmail: 'Correo de trabajo',
  detailsCompany: 'Empresa',
  detailsSubmit: 'Compartir datos',
  detailsDone: '✓ Datos compartidos con el estratega',
  detailsFailed: 'No pude guardar esos datos. Inténtalo de nuevo.',
  callbackTitle: 'Un estratega te llamará',
  callbackBody:
    'Ningún estratega puede entrar ahora mismo, así que registré una devolución de llamada ' +
    'con tus datos. Alguien de Cadre te contactará.',
}

export function chromeFor(language: Language): Chrome {
  return language === 'es' ? ES : EN
}
