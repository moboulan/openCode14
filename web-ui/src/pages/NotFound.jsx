import { Link } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Home } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <Card className="max-w-sm text-center">
        <CardContent className="p-10">
          <p className="text-6xl font-extrabold text-muted-foreground mb-2">404</p>
          <p className="text-sm text-muted-foreground mb-6">Page not found.</p>
          <Button asChild>
            <Link to="/">
              <Home className="mr-2 h-4 w-4" />
              Dashboard
            </Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
