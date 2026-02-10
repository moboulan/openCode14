import * as React from 'react';
import { cn } from '@/lib/utils';

const Badge = React.forwardRef(({ className, variant = 'default', ...props }, ref) => {
	const variants = {
		default: 'bg-primary/15 text-primary border-primary/20',
		secondary: 'bg-secondary text-secondary-foreground border-secondary',
		destructive: 'bg-destructive/15 text-red-400 border-destructive/20',
		outline: 'text-foreground border-border',
		success: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/20',
		warning: 'bg-amber-500/15 text-amber-400 border-amber-500/20',
		info: 'bg-blue-500/15 text-blue-400 border-blue-500/20',
	};
	return (
		<span
			ref={ref}
			className={cn(
				'inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium transition-colors',
				variants[variant],
				className,
			)}
			{...props}
		/>
	);
});
Badge.displayName = 'Badge';

export { Badge };
