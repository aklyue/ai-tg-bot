import { TabsContent } from "@radix-ui/react-tabs";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../ui/card";
import type { Source } from "@/types/admin_page";

function SourcesContent({ sources }: { sources: Source[] }) {
  return (
    <TabsContent value="sources" className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Источники базы знаний</CardTitle>
          <CardDescription>
            Список всех источников информации, подключенных к боту
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {sources.map((source) => (
              <div
                key={source.id}
                className="flex items-center justify-between p-4 border rounded-lg"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{source.name}</span>
                    <span className="px-2 py-0.5 text-xs rounded bg-secondary">
                      {source.type === "website" ? "Сайт" : "Документ"}
                    </span>
                    <span
                      className={`px-2 py-0.5 text-xs rounded ${
                        source.status === "success"
                          ? "bg-green-100 text-green-800"
                          : "bg-yellow-100 text-yellow-800"
                      }`}
                    >
                      {source.status === "success" ? "Успешно" : "Ожидание"}
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground">{source.url}</p>
                  <p className="text-xs text-muted-foreground">
                    Последнее обновление: {source.lastParsed}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </TabsContent>
  );
}

export default SourcesContent;
