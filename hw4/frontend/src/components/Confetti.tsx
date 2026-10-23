import { useState, type CSSProperties } from 'react'

const COLORS = ['#ff4fa3', '#ffffff', '#ff2d8f', '#ffd1e8', '#00356b']

/** A one-time burst of pink-and-white confetti (skipped for reduced motion). */
export default function Confetti({ pieces = 70 }: { pieces?: number }) {
  const [bits] = useState(() => Array.from({ length: pieces }, (_, i) => ({
    left: Math.random() * 100,
    delay: Math.random() * 0.5,
    duration: 1.8 + Math.random() * 1.6,
    drift: (Math.random() - 0.5) * 240,
    spin: (Math.random() - 0.5) * 1080,
    color: COLORS[i % COLORS.length],
    w: 6 + Math.random() * 6,
  })))
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return null
  return (
    <div className="confetti" aria-hidden="true">
      {bits.map((b, i) => (
        <span key={i} style={{
          left: `${b.left}%`, background: b.color, width: b.w, height: b.w * 0.45,
          animationDelay: `${b.delay}s`, animationDuration: `${b.duration}s`,
          '--drift': `${b.drift}px`, '--spin': `${b.spin}deg`,
        } as CSSProperties} />
      ))}
    </div>
  )
}
