import type { KnowledgeItem } from "@/types/admin_page";
import { TabsContent } from "@radix-ui/react-tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";

function KnowledgeBase({ knowledge }: { knowledge: KnowledgeItem[] }) {
  return (
    <TabsContent value="knowledge" className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>База знаний</CardTitle>
          <CardDescription>
            Содержимое векторной базы данных Qdrant
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {knowledge.map((item) => (
              <div key={item.id} className="p-4 border rounded-lg space-y-2">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{item.source}</span>
                  <span className="px-2 py-0.5 text-xs rounded bg-secondary">
                    {item.chunk}
                  </span>
                </div>
                <p className="text-sm text-muted-foreground line-clamp-3">
                  {item.content}
                </p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </TabsContent>
  );
}

export default KnowledgeBase;
