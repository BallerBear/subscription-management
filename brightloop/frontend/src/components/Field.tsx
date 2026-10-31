type Props = {
  label: string;
  name: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  error?: string;
  hint?: string;
  autoComplete?: string;
};

export default function Field({ label, name, value, onChange, type = "text", error, hint, autoComplete }: Props) {
  const id = `field-${name}`;
  const noteId = `${id}-note`;
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        name={name}
        type={type}
        value={value}
        autoComplete={autoComplete}
        onChange={(e) => onChange(e.target.value)}
        aria-invalid={error ? true : undefined}
        aria-describedby={error || hint ? noteId : undefined}
      />
      {error ? (
        <p id={noteId} className="field-error" role="alert">
          {error}
        </p>
      ) : hint ? (
        <p id={noteId} className="field-hint">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
