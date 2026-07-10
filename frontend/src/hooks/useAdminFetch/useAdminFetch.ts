import type { Dialogue, KnowledgeItem, Source } from "@/types/admin_page";
import { useEffect, useState } from "react";
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const useAdminFetch = () => {
  const [sources, setSources] = useState<Source[]>([]);
  const [dialogues, setDialogues] = useState<Dialogue[]>([]);
  const [knowledge, setKnowledge] = useState<KnowledgeItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [useMockData, setUseMockData] = useState(true);
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [sourcesRes, dialoguesRes, knowledgeRes] = await Promise.all([
          fetch(`${API_BASE_URL}/api/sources`).catch(() => null),
          fetch(`${API_BASE_URL}/api/dialogues`).catch(() => null),
          fetch(`${API_BASE_URL}/api/knowledge`).catch(() => null),
        ]);

        if (sourcesRes?.ok) {
          setSources(await sourcesRes.json());
          setUseMockData(false);
        }
        if (dialoguesRes?.ok) {
          setDialogues(await dialoguesRes.json());
        }
        if (knowledgeRes?.ok) {
          setKnowledge(await knowledgeRes.json());
        }
      } catch (error) {
        console.log("API недоступно, используем мок-данные:", error);
        setUseMockData(true);
      }
    };

    fetchData();
  }, []);

  const handleRefresh = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/refresh`, {
        method: "POST",
      });
      if (response.ok) {
        alert("Обновление базы знаний запущено!");
        setTimeout(() => {
          window.location.reload();
        }, 5000);
      } else {
        alert("Ошибка при обновлении базы знаний");
      }
    } catch (error) {
      alert("API недоступно. Запустите backend сервер.");
    } finally {
      setIsLoading(false);
    }
  };
  return {
    sources,
    dialogues,
    knowledge,
    isLoading,
    useMockData,
    handleRefresh,
  };
};
