import { refreshCatalogue } from '../lib/catalogue.ts'

/** Shown when products can't be loaded, with a way to try again. */
export default function LoadError({ message }: { message: string }) {
  return (
    <div className="status status--error loaderror" role="alert">
      <p>Couldn’t load products: {message}.</p>
      <button className="btn btn--primary btn--sm" onClick={() => void refreshCatalogue()}>Try again</button>
    </div>
  )
}
