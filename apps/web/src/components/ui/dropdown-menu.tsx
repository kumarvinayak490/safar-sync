"use client";

import {
  type KeyboardEvent,
  type MouseEvent,
  type ReactNode,
  useEffect,
  useId,
  useRef,
  useState,
} from "react";

import { cn } from "@/lib/utils";

export function DropdownMenu({
  children,
  className,
  menuClassName,
  trigger,
  triggerClassName,
}: {
  children: ReactNode;
  className?: string;
  menuClassName?: string;
  trigger: ReactNode;
  triggerClassName?: string;
}) {
  const [open, setOpen] = useState(false);
  const menuId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) {
      return undefined;
    }

    function handlePointerDown(event: PointerEvent) {
      const target = event.target;

      if (
        target instanceof Node &&
        rootRef.current &&
        !rootRef.current.contains(target)
      ) {
        setOpen(false);
      }
    }

    function handleKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key !== "Escape") {
        return;
      }

      setOpen(false);
      triggerRef.current?.focus();
    }

    document.addEventListener("pointerdown", handlePointerDown, true);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("pointerdown", handlePointerDown, true);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  function handleMenuClick(event: MouseEvent<HTMLDivElement>) {
    const target = event.target;

    if (!(target instanceof Element)) {
      return;
    }

    const submitButton = target.closest('button[type="submit"]:not(:disabled)');
    if (submitButton && rootRef.current?.contains(submitButton)) {
      return;
    }

    const actionable = target.closest("a[href], button:not(:disabled)");
    if (actionable && rootRef.current?.contains(actionable)) {
      setOpen(false);
    }
  }

  function handleTriggerKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    if (event.key !== "ArrowDown" && event.key !== "Enter" && event.key !== " ") {
      return;
    }

    event.preventDefault();
    setOpen(true);
  }

  return (
    <div
      className={cn(className, open ? "is-open" : "")}
      data-open={open ? "true" : "false"}
      ref={rootRef}
    >
      <button
        aria-controls={menuId}
        aria-expanded={open}
        aria-haspopup="true"
        className={triggerClassName}
        onClick={() => setOpen((current) => !current)}
        onKeyDown={handleTriggerKeyDown}
        ref={triggerRef}
        type="button"
      >
        {trigger}
      </button>
      {open ? (
        <div className={menuClassName} id={menuId} onClick={handleMenuClick}>
          {children}
        </div>
      ) : null}
    </div>
  );
}
