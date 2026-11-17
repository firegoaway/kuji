# -*- coding: utf-8 -*-
"""Короткий переключатель-«свитч» вместо чекбоксов (сессия 10, Задача 0).

Плоский горизонтальный переключатель в стиле iOS/Android: трек ~34×18 px,
белый кругляш-кноб, дорожка ACCENT во включённом состоянии и нейтральная
с рамкой BORDER в выключенном. Подпись (если задана) рисуется слева от
трека – как у QCheckBox, поэтому замена в формах точечная.

Совместимость API с QCheckBox (только используемые сайты):
    ToggleSwitch(text) / setText() / text()
    setChecked(bool) / isChecked()
    toggled(bool)            – сигнал QAbstractButton
    setToolTip()             – QWidget

Анимация скольжения 130 мс; мгновенный режим (без анимации) при
QT_QPA_PLATFORM=offscreen или переменной окружения KUJI_NO_ANIMATION –
тот же шов, что у modern_tooltip (оффскрин-тесты не ждут таймеров).

Все цвета – из theme.py (единый источник стиля), без ad-hoc значений.
"""

from __future__ import annotations

import os

from PySide6.QtCore import (QEasingCurve, QSize, Qt, QVariantAnimation)
from PySide6.QtGui import QColor, QFontMetrics, QPainter
from PySide6.QtWidgets import QAbstractButton, QWidget

from .theme import (PANEL_BG, QCOLOR, TEXT_PRIMARY, TEXT_SECONDARY)

TRACK_W = 34          # ширина дорожки
TRACK_H = 18          # высота дорожки
KNOB_D = 14           # диаметр кноба
TRACK_PAD = 2         # поле между кнобом и краем дорожки
TEXT_GAP = 8          # зазор подпись ↔ трек
ANIM_MS = 130         # длительность скольжения (120–150 мс)


def _instant_mode() -> bool:
    """Мгновенный режим: оффскрин или явный флаг отключения анимации."""
    return (os.environ.get("KUJI_NO_ANIMATION") == "1"
            or os.environ.get("QT_QPA_PLATFORM", "").startswith("offscreen"))


class ToggleSwitch(QAbstractButton):
    """Короткий переключатель с необязательной подписью слева."""

    def __init__(self, text: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self._text = text
        self._pos = 0.0            # 0.0 = выкл, 1.0 = вкл (анимируется)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(ANIM_MS)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_anim)
        self.toggled.connect(self._on_toggled)
        # Сессия 12, Задача 7: подсказки по умолчанию НЕТ – дублировать
        # подпись строки бессмысленно; содержательные тексты задают
        # места применения (инспектор: вентиляция/молниезащита/меры из БД)

    # ---------- API подписи ----------
    def setText(self, text: str) -> None:
        self._text = text
        self.updateGeometry()
        self.update()

    def text(self) -> str:          # noqa: N802 (Qt-стиль)
        return self._text

    # ---------- анимация ----------
    def _on_toggled(self, on: bool) -> None:
        if _instant_mode() or not self.isVisible():
            self._pos = 1.0 if on else 0.0
            self._anim.stop()
            self.update()
            return
        self._anim.stop()
        self._anim.setStartValue(float(self._pos))
        self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    def _on_anim(self, v: float) -> None:
        self._pos = float(v)
        self.update()

    # ---------- геометрия ----------
    def sizeHint(self) -> QSize:    # noqa: N802 (Qt-стиль)
        fm = QFontMetrics(self.font())
        text_w = fm.horizontalAdvance(self._text) if self._text else 0
        w = text_w + (TEXT_GAP + TRACK_W if self._text else 0)
        h = max(TRACK_H, fm.height())
        return QSize(max(w, TRACK_W), h)

    def minimumSizeHint(self) -> QSize:   # noqa: N802 (Qt-стиль)
        return QSize(TRACK_W, TRACK_H)

    # ---------- отрисовка (плоско, без теней/градиентов) ----------
    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if not self.isEnabled():
            p.setOpacity(0.45)

        h = height = self.height()
        track_h = min(TRACK_H, h)
        ty = (h - track_h) / 2.0
        tx = self.width() - TRACK_W

        # подпись слева (с эллипсисом до доступной ширины)
        if self._text:
            fm = QFontMetrics(self.font())
            avail = max(0, tx - TEXT_GAP)
            label = fm.elidedText(self._text, Qt.TextElideMode.ElideRight,
                                  avail)
            p.setPen(QColor(TEXT_PRIMARY if self.isEnabled()
                            else TEXT_SECONDARY))
            p.drawText(0, 0, avail, h,
                       int(Qt.AlignmentFlag.AlignVCenter
                           | Qt.AlignmentFlag.AlignLeft), label)

        # дорожка
        track = QCOLOR["accent"] if self.isChecked() else QCOLOR["border"]
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(tx, ty, TRACK_W, track_h,
                          track_h / 2.0, track_h / 2.0)

        # кноб: скольжение TRACK_PAD → TRACK_W − KNOB_D − TRACK_PAD
        span = TRACK_W - KNOB_D - 2 * TRACK_PAD
        kx = tx + TRACK_PAD + span * self._pos
        ky = ty + (track_h - KNOB_D) / 2.0
        p.setBrush(QColor(PANEL_BG))
        p.drawEllipse(kx, ky, KNOB_D, KNOB_D)

    # ---------- клавиатура/фокус ----------
    # Space/Enter переключают – стандарт QAbstractButton; дополнительных
    # привязок не вводим, родительские шорткаты не перехватываем.


def bind_fields(switch: ToggleSwitch, *fields: QWidget,
                initial: bool | None = None) -> None:
    """Живая связь «переключатель → поля»: поля, имеющие смысл только при
    включённом переключателе, показываются/скрываются вместе с ним.

    initial – исходное состояние (по умолчанию берётся сам переключатель);
    вызывается после setChecked(), поэтому стартовая видимость корректна.
    """
    state = switch.isChecked() if initial is None else initial

    def apply(on: bool) -> None:
        for w in fields:
            w.setVisible(on)

    apply(state)
    switch.toggled.connect(apply)
