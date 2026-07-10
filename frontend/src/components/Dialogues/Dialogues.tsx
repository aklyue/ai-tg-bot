import type { Dialogue } from "@/types/admin_page";
import { TabsContent } from "@radix-ui/react-tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";

function Dialogues({ dialogues }: { dialogues: Dialogue[] }) {
  return (
    <TabsContent value="dialogues" className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>История диалогов</CardTitle>
          <CardDescription>
            Последние запросы пользователей и ответы бота
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {dialogues.map((dialogue) => (
              <div
                key={dialogue.id}
                className="p-4 border rounded-lg space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{dialogue.userName}</span>
                    <span className="text-xs text-muted-foreground">
                      ID: {dialogue.userId}
                    </span>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {dialogue.timestamp}
                  </span>
                </div>
                <div className="space-y-2">
                  <div>
                    <span className="text-sm font-medium">Вопрос: </span>
                    <span className="text-sm">{dialogue.question}</span>
                  </div>
                  <div>
                    <span className="text-sm font-medium">Ответ: </span>
                    <span className="text-sm text-muted-foreground">
                      {dialogue.answer}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </TabsContent>
  );
}

export default Dialogues;
