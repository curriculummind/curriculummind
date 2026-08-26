/** The CurriculumMind wordmark: a small connected-node graph, echoing the real Concept/Standard graph in the data model, next to the product name. */
export function Logo({ className = "" }: { className?: string }) {
  return (
    <div className={`flex items-center gap-3 font-display text-lg font-medium text-ink ${className}`}>
      <svg width="26" height="26" viewBox="0 0 30 30" fill="none">
        <circle cx="15" cy="6" r="3" className="fill-gold" />
        <circle cx="5" cy="23" r="3" className="fill-gold" />
        <circle cx="25" cy="23" r="3" className="fill-gold" />
        <path
          d="M15 9L6.5 20.5M15 9L23.5 20.5M7.8 23H22.2"
          className="stroke-gold"
          strokeWidth="1.1"
          strokeOpacity="0.7"
        />
      </svg>
      CurriculumMind
    </div>
  );
}
