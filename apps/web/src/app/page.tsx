export default function Home() {
  return (
    <div className="mx-auto flex min-h-svh max-w-6xl flex-col px-6 sm:px-10">
      <header className="border-b border-border py-7">
        <span className="text-lg font-semibold tracking-tight">Opportunity Tracker<span className="text-primary">.</span></span>
      </header>
      <main id="main-content" className="flex flex-1 flex-col justify-center py-20 sm:py-28">
        <p className="mb-5 text-sm font-medium tracking-widest text-muted uppercase">Your next chapter</p>
        <h1 className="max-w-3xl text-4xl leading-tight font-semibold tracking-tight sm:text-6xl">
          A little direction.<br />A world of <span className="text-primary">opportunity.</span>
        </h1>
        <p className="mt-6 max-w-lg text-lg leading-relaxed text-muted">
          A space to discover internships, scholarships and academic programs — and keep your next steps in sight.
        </p>
        <section aria-labelledby="getting-started" className="mt-12 max-w-lg rounded-card border border-border p-6 sm:p-8">
          <h2 id="getting-started" className="text-lg font-semibold">Something good is taking shape.</h2>
          <p className="mt-2 text-sm leading-relaxed text-muted">
            We’re building Opportunity Tracker. Opportunity discovery and application tracking are coming soon.
          </p>
        </section>
      </main>
      <footer className="border-t border-border py-6 text-sm text-muted">Made for students. Built around possibility.</footer>
    </div>
  );
}
