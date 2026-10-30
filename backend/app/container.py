"""Monta banco, repositórios e serviços uma única vez por processo."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.curriculum.registry import CurriculumRegistry
from app.db import Database
from app.repositories.course_repo import CourseRepository
from app.repositories.lesson_repo import LessonRepository
from app.repositories.progress_repo import ProgressRepository
from app.repositories.session_repo import SessionRepository
from app.repositories.settings_repo import ProfileRepository, SettingsRepository
from app.repositories.vocabulary_repo import VocabularyRepository
from app.services.conversation_service import ConversationService
from app.services.course_service import CourseService
from app.services.curriculum_builder import CurriculumBuilder
from app.services.lesson_service import LessonService
from app.repositories.analysis_repo import AnalysisRepository
from app.services.level_analysis import LevelAnalysisService
from app.services.llm_service import OllamaClient
from app.services.prompt_library import PromptLibrary
from app.services.speech_client import SpeechClient
from app.services.study_material import StudyMaterialService


@dataclass
class Container:
    config: Settings
    db: Database
    llm: OllamaClient
    speech: SpeechClient
    prompts: PromptLibrary
    settings: SettingsRepository
    profiles: ProfileRepository
    sessions: SessionRepository
    vocabulary: VocabularyRepository
    lessons: LessonRepository
    progress: ProgressRepository
    conversation: ConversationService
    lesson_service: LessonService
    course: CourseService
    curriculum: CurriculumRegistry
    curriculum_builder: CurriculumBuilder
    level_analysis: LevelAnalysisService
    analyses: AnalysisRepository
    study_material: StudyMaterialService


def build_container(config: Settings, *, llm: OllamaClient | None = None,
                    speech: SpeechClient | None = None) -> Container:
    db = Database(config.db_path, config.migrations_dir, config.backups_dir)
    db.migrate()

    llm = llm or OllamaClient(config.ollama_url, config.llm_timeout_s)
    speech = speech or SpeechClient(config.speech_url, config.speech_timeout_s)
    prompts = PromptLibrary(config.prompts_dir)
    user_curriculum = config.data_dir / "curriculo_usuario"
    curriculum = CurriculumRegistry.load(config.curriculum_dir, user_curriculum)

    settings = SettingsRepository(db)
    profiles = ProfileRepository(db)
    sessions = SessionRepository(db)
    vocabulary = VocabularyRepository(db)
    lessons = LessonRepository(db)
    progress = ProgressRepository(db)

    conversation = ConversationService(
        config=config,
        sessions=sessions,
        vocabulary=vocabulary,
        profiles=profiles,
        settings=settings,
        progress=progress,
        llm=llm,
        prompts=prompts,
    )
    lesson_service = LessonService(
        lessons=lessons,
        profiles=profiles,
        settings=settings,
        llm=llm,
        prompts=prompts,
        default_model=config.default_llm_model,
    )
    course = CourseService(
        registry=curriculum,
        repo=CourseRepository(db),
        settings=settings,
        llm=llm,
        prompts=prompts,
        speech=speech,
        default_model=config.default_llm_model,
    )
    builder = CurriculumBuilder(
        registry=curriculum,
        repo=CourseRepository(db),
        settings=settings,
        llm=llm,
        prompts=prompts,
        default_model=config.default_llm_model,
        curriculum_root=config.curriculum_dir,
        user_root=user_curriculum,
    )
    analyses = AnalysisRepository(db)
    level_analysis = LevelAnalysisService(
        sessions=sessions,
        profiles=profiles,
        settings=settings,
        llm=llm,
        repo=analyses,
        prompt_path=config.prompts_dir / "analysis" / "level_analysis.txt",
        default_model=config.default_llm_model,
    )
    study_material = StudyMaterialService(
        sessions=sessions,
        vocabulary=vocabulary,
        profiles=profiles,
        settings=settings,
        llm=llm,
        prompt_path=config.prompts_dir / "material" / "exercicio_lacunas.txt",
        default_model=config.default_llm_model,
    )
    return Container(
        config=config,
        db=db,
        llm=llm,
        speech=speech,
        prompts=prompts,
        settings=settings,
        profiles=profiles,
        sessions=sessions,
        vocabulary=vocabulary,
        lessons=lessons,
        progress=progress,
        conversation=conversation,
        lesson_service=lesson_service,
        course=course,
        curriculum=curriculum,
        curriculum_builder=builder,
        level_analysis=level_analysis,
        analyses=analyses,
        study_material=study_material,
    )
