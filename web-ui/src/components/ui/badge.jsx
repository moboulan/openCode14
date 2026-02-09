import * as React from "react";
import { cn } from "@/lib/utils";

const Badge = React.forwardRef(({ className, variant = "default", ...props }, ref) => {
	const variants = {
		default: "bg-primary text-primary-foreground",
		secondary: "bg-secondary text-secondary-foreground",
		destructive: "bg-destructive text-destructive-foreground",
		outline: "border border-border text-foreground",
		critical: "bg-severity-critical/15 text-severity-critical border border-severity-critical/25",
		high: "bg-severity-high/15 text-severity-high border border-severity-high/25",
		medium: "bg-severity-medium/15 text-severity-medium border border-severity-medium/25",
		low: "bg-severity-low/15 text-severity-low border border-severity-low/25",
		open: "bg-status-open/15 text-status-open border border-status-open/25",
		acknowledged: "bg-status-acknowledged/15 text-status-acknowledged border border-status-acknowledged/25",
		resolved: "bg-status-resolved/15 text-status-resolved border border-status-resolved/25",
	};

	return (
		<span
			ref={ref}
			className={cn(
				"inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium transition-colors",
				variants[variant] || variants.default,
				className
			)}
			{...props}
		/>
	);
});
Badge.displayName = "Badge";

export { Badge };
