import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex min-h-6 w-fit items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground",
        secondary: "border-border bg-secondary text-secondary-foreground",
        outline: "border-border bg-card text-foreground",
        success:
          "border-[oklch(0.76_0.058_150)] bg-[oklch(0.95_0.028_150)] text-[oklch(0.36_0.085_150)]",
        warning:
          "border-[oklch(0.76_0.055_252)] bg-[oklch(0.942_0.034_252)] text-[oklch(0.3_0.074_258)]",
        info: "border-[oklch(0.78_0.05_238)] bg-[oklch(0.955_0.02_238)] text-[oklch(0.38_0.075_238)]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
