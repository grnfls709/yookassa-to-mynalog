name: Багрепорт / Bug report
title: "[BUG] "
description: Сообщите о возникшей проблеме

body:
  - type: markdown
    attributes:
      value: |
        ## Прежде чем создать проблему, пожалуйста, убедитесь, что:
        1. Вы указали четкий и краткий заголовок проблемы, чтобы другие могли быстро её найти.
        2. Вы проверили, что похожей проблемы нет среди [существующих](https://github.com/grnfls709/yookassa-to-mynalog/issues?q=is%3Aissue), в противном случае, обсуждайте её там.
        3. Вы подробно описали проблему, следуя требованиям шаблона, иначе проблема будет закрыта без рассмотрения.
  - type: textarea
    id: description
    attributes:
      label: Описание проблемы
      description: Подробно и ясно опишите возникшую у вас проблему, при возможности приложите скриншоты
    validations:
      required: true
  - type: textarea
    attributes:
      label: Версия
      description: Пожалуйста, укажите конкретную версию скрипта yookassa-to-mynalog
    validations:
      required: true
  - type: textarea
    attributes:
      label: Как воспроизвести
      description: Опишите шаги для воспроизведения ошибки
    validations:
      required: true
  - type: dropdown
    attributes:
      label: Операционная система
      options:
        - Android
        - Windows
        - MacOS
        - Linux
    validations:
      required: true
  - type: textarea
    attributes:
      label: Логи (не прикрепляйте файл, вставьте содержимое логов напрямую)
      description: Пожалуйста, предоставьте полный или соответствующий отладочный лог (для этого введите команду python main.py из тестовой среды или используйте docker compose в серверной среде)
    validations:
      required: true
