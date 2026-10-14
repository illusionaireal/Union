import { useEffect, useRef, type ReactNode } from 'react';
import { X } from 'lucide-react';
export function Dialog({
  id,
  title,
  closeId,
  onClose,
  children,
}: {
  id: string;
  title: string;
  closeId: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current!;
    const trigger = document.activeElement as HTMLElement | null;
    dialog.showModal();
    return () => {
      dialog.close();
      trigger?.focus({ preventScroll: true });
    };
  }, []);
  const titleId = id === 'detail-dialog' ? 'detail-title' : 'operation-title';
  return (
    <dialog
      ref={ref}
      id={id}
      aria-labelledby={titleId}
      onCancel={onClose}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="dialog-inner">
        <div className="dialog-header">
          <div>
            <div className="eyebrow">ORGANIZATION WORKSPACE</div>
            <h2 id={titleId}>{title}</h2>
          </div>
          <button id={closeId} className="icon-button" aria-label="关闭" onClick={onClose}>
            <X size={20} />
          </button>
        </div>
        {children}
      </div>
    </dialog>
  );
}
