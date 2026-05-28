import { useEffect, useState } from 'react';

export function ApiActivityIndicator() {
  const [active, setActive] = useState(0);

  useEffect(() => {
    const onStart = () => setActive((a) => a + 1);
    const onEnd = () => setActive((a) => Math.max(0, a - 1));
    window.addEventListener('squirrel:api-start', onStart);
    window.addEventListener('squirrel:api-end', onEnd);
    return () => {
      window.removeEventListener('squirrel:api-start', onStart);
      window.removeEventListener('squirrel:api-end', onEnd);
    };
  }, []);

  if (active === 0) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-[100] h-0.5 bg-primary/80 animate-pulse pointer-events-none" />
  );
}
