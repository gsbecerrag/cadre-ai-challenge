/**
 * The placeholder chat page. The chat shell is deliberately empty and the composer is
 * disabled: this slice proves the deploy, not the Assistant.
 */
export function App() {
  return (
    <div className="min-h-screen bg-linear-to-b from-cadre-sand-dark to-cadre-sand font-sans text-cadre-body">
      <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center gap-8 px-6 py-16">
        <header className="space-y-3">
          <h1 className="font-display text-5xl font-semibold tracking-tight text-cadre-red">
            Cadre AI
          </h1>
          <p className="text-lg text-cadre-muted">
            Ask about our services, industries, the AI Maturity Index, or talk to a strategist.
          </p>
        </header>

        <section
          aria-label="Chat"
          className="flex flex-col overflow-hidden rounded-card border border-cadre-line bg-white"
        >
          <div className="flex min-h-64 items-center justify-center px-6 py-10 text-center text-sm text-cadre-muted">
            The Assistant is not answering yet.
          </div>

          <form
            className="flex items-center gap-3 border-t border-cadre-line bg-cadre-sand px-4 py-4"
            onSubmit={(event) => event.preventDefault()}
          >
            <input
              type="text"
              aria-label="Message the Assistant"
              placeholder="coming soon"
              disabled
              className="min-w-0 flex-1 rounded-pill border border-cadre-line bg-white px-5 py-3 text-base text-cadre-body placeholder:text-cadre-muted disabled:cursor-not-allowed"
            />
            <button
              type="submit"
              disabled
              className="rounded-pill bg-cadre-ink px-6 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40"
            >
              Send
            </button>
          </form>
        </section>
      </main>
    </div>
  )
}
