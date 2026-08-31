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
  connectionError: string
}

const EN: Chrome = {
  headerTitle: 'Cadre AI Assistant',
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
  connectionError:
    'I lost the connection before I could answer. Please try again — or reach the team at ' +
    'hello@gocadre.ai or (619) 324-3223.',
}

const ES: Chrome = {
  headerTitle: 'Asistente de Cadre AI',
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
  connectionError:
    'Perdí la conexión antes de poder responder. Inténtalo de nuevo — o escribe a ' +
    'hello@gocadre.ai o llama al (619) 324-3223.',
}

export function chromeFor(language: Language): Chrome {
  return language === 'es' ? ES : EN
}
