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
        character_pronouns = character.pronouns or 'не указаны'
        return (
            '\n\nНастройки роли и обращения:\n'
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
