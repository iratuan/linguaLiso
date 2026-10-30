-- Personalidade do professor escolhida para cada conversa (formal, descontraido ou nativo).
-- Conversas antigas recebem o padrão, que é o mesmo tom que elas já usavam.

ALTER TABLE conversation_sessions ADD COLUMN persona TEXT NOT NULL DEFAULT 'descontraido';
