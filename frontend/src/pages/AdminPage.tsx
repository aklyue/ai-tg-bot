import Dialogues from "@/components/Dialogues";
import KnowledgeBase from "@/components/KnowledgeBase";
import SourcesContent from "@/components/SourcesContent";
import { Button } from "@/components/ui/button";
import useAdminFetch from "@/hooks/useAdminFetch";
import { Tabs, TabsList, TabsTrigger } from "@radix-ui/react-tabs";
import {
  Database,
  FileText,
  Loader2,
  MessageSquare,
  RefreshCw,
} from "lucide-react";

function AdminPage() {
  const {
    sources,
    dialogues,
    knowledge,
    isLoading,
    useMockData,
    handleRefresh,
  } = useAdminFetch();
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Database className="h-6 w-6" />
            <h1 className="text-xl font-bold">Админка бота</h1>
          </div>
          <div className="flex items-center gap-4">
            {useMockData && (
              <span className="text-xs text-muted-foreground px-2 py-1 bg-yellow-100 rounded">
                Мок-данные
              </span>
            )}
            <Button
              onClick={handleRefresh}
              variant="outline"
              disabled={isLoading}
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4 mr-2" />
              )}
              Переобновить базу
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6">
        <Tabs defaultValue="sources" className="space-y-6">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="sources">
              <FileText className="h-4 w-4 mr-2" />
              Источники
            </TabsTrigger>
            <TabsTrigger value="knowledge">
              <Database className="h-4 w-4 mr-2" />
              База знаний
            </TabsTrigger>
            <TabsTrigger value="dialogues">
              <MessageSquare className="h-4 w-4 mr-2" />
              Диалоги
            </TabsTrigger>
          </TabsList>

          <SourcesContent sources={sources} />

          {/* Вкладка База знаний */}
          <KnowledgeBase knowledge={knowledge} />

          {/* Вкладка Диалоги */}
          <Dialogues dialogues={dialogues} />
        </Tabs>
      </main>
    </div>
  );
}

export default AdminPage;
