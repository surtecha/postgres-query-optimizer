import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
const variants = cva("button", {variants: {variant: {default: "primary", secondary: "secondary"}}, defaultVariants: {variant: "default"}});
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof variants> { asChild?: boolean }
export function Button({className, variant, asChild = false, ...props}: ButtonProps) {
  const Component = asChild ? Slot : "button";
  return <Component className={cn(variants({variant}), className)} {...props}/>;
}
