import { useNavigate } from 'react-router-dom';
import { AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function NotFound() {
	const navigate = useNavigate();

	return (
		<div className="flex flex-col items-center justify-center min-h-[60vh] text-center fade-in">
			<AlertTriangle className="h-16 w-16 text-muted-foreground mb-4" />
			<h1 className="text-2xl font-bold">Page Not Found</h1>
			<p className="text-sm text-muted-foreground mt-2 mb-6">The page you're looking for doesn't exist or has been moved.</p>
			<Button onClick={() => navigate('/')}>Back to Dashboard</Button>
		</div>
	);
}
