export function Banners({ warnings, kind = "warn" }: { warnings: string[]; kind?: "warn" | "error" }) {
  if (warnings.length === 0) return null;
  return (
    <>
      {warnings.map((w) => (
        <div key={w} className={`banner ${kind}`}>
          {w}
        </div>
      ))}
    </>
  );
}
