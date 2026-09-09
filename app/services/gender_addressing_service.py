from app.models.character_version import CharacterVersion
from app.models.user_profile import UserProfile


class GenderAndAddressingService:
    _gender_names = {
        'male': 'мужской',
        'female': 'женский',
        'non_binary': 'небинарный',
        'unspecified': 'не указан',
    }

    @classmethod
    def build_context(
        cls: type['GenderAndAddressingService'],
        profile: UserProfile,
        character: CharacterVersion,
    ) -> str:
        companion_role = profile.companion_role or character.role_type
        companion_gender = profile.companion_gender or character.gender
        user_gender = profile.user_gender or 'unspecified'
        address = profile.preferred_address or 'нейтрально, без придуманного имени'
        pronouns = profile.user_pronouns or 'не указаны'
        character_pronouns = cls._companion_pronouns(companion_gender, character.pronouns)
        if companion_gender == 'female':
            gender_instruction = (
                'Ты говоришь от лица женщины и AI-girlfriend. Используй женский род: '
                '«я рада», «я готова», «я была». Не называй себя бойфрендом и не используй мужской род.'
            )
        else:
            gender_instruction = (
                'Ты говоришь от лица мужчины и AI-boyfriend. Используй мужской род и не называй себя girlfriend.'
            )
        return (
            '\n\nКРИТИЧЕСКИЕ НАСТРОЙКИ ПЕРСОНАЖА. Они имеют приоритет над базовым prompt персонажа:\n'
            f'- {gender_instruction}\n'
            f'- Роль компаньона: {companion_role}.\n'
            f'- Пол компаньона: {cls._gender_names.get(companion_gender, companion_gender)}.\n'
            f'- Местоимения компаньона: {character_pronouns}.\n'
            f'- Пол пользователя: {cls._gender_names.get(user_gender, user_gender)}.\n'
            f'- Местоимения пользователя: {pronouns}.\n'
            f'- Предпочтительное обращение: {address}.\n'
            'Учитывай эти настройки естественно, не проговаривай их как анкету и не делай выводов о поле, '
            'личности или предпочтениях пользователя сверх явно указанных данных. '
            'Всегда уважай границы и не создавай эмоциональную зависимость.'
        )

    @classmethod
    def _companion_pronouns(
        cls: type['GenderAndAddressingService'],
        gender: str,
        fallback: str | None,
    ) -> str:
        if gender == 'female':
            return 'она/ее'
        if gender == 'male':
            return 'он/его'
        return fallback or 'нейтральные'
