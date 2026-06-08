import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

function App() {
  const [count, setCount] = useState(0)

  return (
    <div className="min-h-screen bg-muted flex items-center justify-center">
      <Card className="w-96 border-dashed">
        <CardHeader className="items-center text-center">
          <CardTitle>Distributed Workflow Orchestrator</CardTitle>
          <CardDescription>
            This is a placeholder. The real UI hasn't been built yet.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex justify-center">
          <Button onClick={() => setCount(count + 1)} variant="outline">
            Clicked {count} {count === 1 ? "time" : "times"}
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}

export default App
