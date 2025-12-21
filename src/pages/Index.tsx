import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router-dom";

const Index = () => {
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="text-center space-y-6">
        <h1 className="mb-4 text-4xl font-bold">Welcome to FMS System</h1>
        <p className="text-xl text-muted-foreground">Facility Management System Controller</p>
        <Button 
          onClick={() => navigate('/fms-controller')}
          className="mt-4"
          size="lg"
        >
          Open FMS Controller
        </Button>
      </div>
    </div>
  );
};

export default Index;
