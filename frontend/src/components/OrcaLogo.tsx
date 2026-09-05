export function OrcaLogo({ className = "h-8 w-8" }: { className?: string }) {
  return (
    <svg viewBox="0 0 48 48" className={className} role="img" aria-label="ORCA logo">
      <circle cx="24" cy="24" r="23" fill="var(--plum)" />
      <path
        d="M8 30c3.6 0 3.6-3.4 7.2-3.4S18.8 30 22.4 30s3.6-3.4 7.2-3.4S33.2 30 36.8 30 40.4 26.6 44 26.6"
        fill="none"
        stroke="var(--blush)"
        strokeWidth="2.4"
        strokeLinecap="round"
        transform="translate(-2 2)"
      />
      <path
        d="M12 20c4-7 11-11 20-11-1.5 5.5-5 9.5-10 11.5 2 .6 4.2.6 6.4 0-2.4 3.6-6.6 5.4-11 4.6-3-.6-5-2.6-5.4-5.1z"
        fill="var(--shell)"
      />
      <circle cx="20.5" cy="18.5" r="1.5" fill="var(--abyss)" />
    </svg>
  );
}
