"""Adapter exposing the existing Ollama agent orchestrator through LLMAgentPort."""

from app.agents import orchestrator
from app.agents.orchestrator import OllamaConfig
from app.domain.ports import AgentAnalysisResult, LLMAgentPort


class OllamaOrchestratorAdapter(LLMAgentPort):
    def __init__(self, config: OllamaConfig) -> None:
        self._config = config

    async def analyze(self, titulo: str, descripcion: str) -> AgentAnalysisResult:
        run = await orchestrator.orchestrate(
            titulo=titulo,
            descripcion=descripcion,
            config=self._config,
        )
        data = run.analysis

        # Defaults mirror the fallbacks the caller applied before this port existed.
        return AgentAnalysisResult(
            tipo=data.get("tipo", "incidente"),
            categoria=data.get("categoria", "General"),
            subcategoria=data.get("subcategoria"),
            confianza_clasificacion=data.get("confianza_clasificacion"),
            razon_clasificacion=data.get("razon_clasificacion"),
            prioridad=data.get("prioridad", "P3"),
            impacto=data.get("impacto"),
            urgencia=data.get("urgencia"),
            area_responsable=data.get("area_responsable"),
            razon_prioridad=data.get("razon_prioridad"),
            respuesta_estructurada=data.get("respuesta_estructurada"),
            respuesta_usuario=data.get("respuesta_usuario"),
            es_recurrente=bool(data.get("es_recurrente", False)),
            causa_raiz=data.get("causa_raiz"),
            accion_preventiva=data.get("accion_preventiva"),
            traces=list(run.traces),
        )
