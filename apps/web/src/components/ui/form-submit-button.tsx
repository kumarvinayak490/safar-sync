"use client";

import { type ButtonHTMLAttributes, type ReactNode } from "react";
import { useFormStatus } from "react-dom";

export function FormSubmitButton({
  children,
  disabled,
  pendingChildren,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  pendingChildren?: ReactNode;
}) {
  const { pending } = useFormStatus();

  return (
    <button
      {...props}
      aria-busy={pending}
      data-pending={pending ? "true" : undefined}
      disabled={disabled || pending}
      type="submit"
    >
      {pending ? (pendingChildren ?? children) : children}
    </button>
  );
}
