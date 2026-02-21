interface AlertProps {
  type?: 'error' | 'success';
  message: string;
}

export default function Alert({ type = 'error', message }: AlertProps) {
  if (!message) return null;
  return <div className={`alert ${type === 'success' ? 'success' : ''}`}>{message}</div>;
}
