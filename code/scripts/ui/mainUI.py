# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main.ui'
##
## Created by: Qt User Interface Compiler version 6.10.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFrame,
    QHBoxLayout, QLabel, QLayout, QLineEdit,
    QMainWindow, QPushButton, QSizePolicy, QSpacerItem,
    QSpinBox, QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1219, 903)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.centralwidget.setStyleSheet(u"")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.card = QFrame(self.centralwidget)
        self.card.setObjectName(u"card")
        self.card.setEnabled(True)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.card.sizePolicy().hasHeightForWidth())
        self.card.setSizePolicy(sizePolicy)
        self.card.setFrameShape(QFrame.NoFrame)
        self.cardLayout = QVBoxLayout(self.card)
        self.cardLayout.setObjectName(u"cardLayout")
        self.topBarLayout = QHBoxLayout()
        self.topBarLayout.setObjectName(u"topBarLayout")
        self.brandingLayout = QHBoxLayout()
        self.brandingLayout.setObjectName(u"brandingLayout")
        self.logoLabel = QLabel(self.card)
        self.logoLabel.setObjectName(u"logoLabel")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.logoLabel.sizePolicy().hasHeightForWidth())
        self.logoLabel.setSizePolicy(sizePolicy1)
        self.logoLabel.setMinimumSize(QSize(0, 0))
        self.logoLabel.setPixmap(QPixmap(u":/icons/icons/logo_biale.svg"))
        self.logoLabel.setScaledContents(False)
        self.logoLabel.setAlignment(Qt.AlignCenter)

        self.brandingLayout.addWidget(self.logoLabel)


        self.topBarLayout.addLayout(self.brandingLayout)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.topBarLayout.addItem(self.horizontalSpacer)

        self.loginLayout = QHBoxLayout()
        self.loginLayout.setSpacing(9)
        self.loginLayout.setObjectName(u"loginLayout")
        self.emailInput = QLineEdit(self.card)
        self.emailInput.setObjectName(u"emailInput")
        font = QFont()
        font.setPointSize(11)
        self.emailInput.setFont(font)

        self.loginLayout.addWidget(self.emailInput)

        self.passwordInput = QLineEdit(self.card)
        self.passwordInput.setObjectName(u"passwordInput")
        self.passwordInput.setFont(font)
        self.passwordInput.setEchoMode(QLineEdit.Normal)

        self.loginLayout.addWidget(self.passwordInput)

        self.logInBnt = QPushButton(self.card)
        self.logInBnt.setObjectName(u"logInBnt")
        font1 = QFont()
        font1.setPointSize(11)
        font1.setBold(True)
        self.logInBnt.setFont(font1)
        self.logInBnt.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.loginLayout.addWidget(self.logInBnt)

        self.language_icon = QLabel(self.card)
        self.language_icon.setObjectName(u"language_icon")
        sizePolicy1.setHeightForWidth(self.language_icon.sizePolicy().hasHeightForWidth())
        self.language_icon.setSizePolicy(sizePolicy1)
        font2 = QFont()
        font2.setPointSize(8)
        self.language_icon.setFont(font2)
        self.language_icon.setPixmap(QPixmap(u":/icons/icons/languages.png"))

        self.loginLayout.addWidget(self.language_icon)

        self.langCombo = QComboBox(self.card)
        self.langCombo.addItem("")
        self.langCombo.addItem("")
        self.langCombo.addItem("")
        self.langCombo.setObjectName(u"langCombo")
        self.langCombo.setFont(font)

        self.loginLayout.addWidget(self.langCombo)


        self.topBarLayout.addLayout(self.loginLayout)


        self.cardLayout.addLayout(self.topBarLayout)

        self.controlsFrame = QFrame(self.card)
        self.controlsFrame.setObjectName(u"controlsFrame")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.controlsFrame.sizePolicy().hasHeightForWidth())
        self.controlsFrame.setSizePolicy(sizePolicy2)
        self.controlsFrame.setMinimumSize(QSize(0, 70))
        self.controlsFrame.setMaximumSize(QSize(16777215, 70))
        self.controlsFrame.setBaseSize(QSize(0, 0))
        self.controlsFrame.setFrameShape(QFrame.NoFrame)
        self.controlsLayout = QHBoxLayout(self.controlsFrame)
        self.controlsLayout.setSpacing(9)
        self.controlsLayout.setObjectName(u"controlsLayout")
        self.controlsLayout.setContentsMargins(3, -1, 3, -1)
        self.randomAnimButton = QPushButton(self.controlsFrame)
        self.randomAnimButton.setObjectName(u"randomAnimButton")
        sizePolicy1.setHeightForWidth(self.randomAnimButton.sizePolicy().hasHeightForWidth())
        self.randomAnimButton.setSizePolicy(sizePolicy1)
        font3 = QFont()
        font3.setPointSize(11)
        font3.setBold(False)
        self.randomAnimButton.setFont(font3)
        self.randomAnimButton.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon = QIcon()
        icon.addFile(u":/icons/icons/shuffle.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.randomAnimButton.setIcon(icon)
        self.randomAnimButton.setIconSize(QSize(20, 20))

        self.controlsLayout.addWidget(self.randomAnimButton)

        self.randomButton = QPushButton(self.controlsFrame)
        self.randomButton.setObjectName(u"randomButton")
        sizePolicy1.setHeightForWidth(self.randomButton.sizePolicy().hasHeightForWidth())
        self.randomButton.setSizePolicy(sizePolicy1)
        self.randomButton.setFont(font)
        self.randomButton.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.randomButton.setLayoutDirection(Qt.LeftToRight)
        self.randomButton.setIcon(icon)
        self.randomButton.setIconSize(QSize(20, 20))

        self.controlsLayout.addWidget(self.randomButton)

        self.horizontalSpacer_7 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.controlsLayout.addItem(self.horizontalSpacer_7)

        self.browseButton = QPushButton(self.controlsFrame)
        self.browseButton.setObjectName(u"browseButton")
        self.browseButton.setFont(font1)
        self.browseButton.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon1 = QIcon()
        icon1.addFile(u":/icons/icons/images_blue.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.browseButton.setIcon(icon1)
        self.browseButton.setIconSize(QSize(20, 20))

        self.controlsLayout.addWidget(self.browseButton)


        self.cardLayout.addWidget(self.controlsFrame)

        self.upload_box_v_box_layout = QVBoxLayout()
        self.upload_box_v_box_layout.setObjectName(u"upload_box_v_box_layout")
        self.add_file_h_layout = QHBoxLayout()
        self.add_file_h_layout.setObjectName(u"add_file_h_layout")
        self.add_files_icon = QLabel(self.card)
        self.add_files_icon.setObjectName(u"add_files_icon")
        sizePolicy1.setHeightForWidth(self.add_files_icon.sizePolicy().hasHeightForWidth())
        self.add_files_icon.setSizePolicy(sizePolicy1)
        self.add_files_icon.setPixmap(QPixmap(u":/icons/icons/upload.png"))

        self.add_file_h_layout.addWidget(self.add_files_icon)

        self.add_file_label = QLabel(self.card)
        self.add_file_label.setObjectName(u"add_file_label")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.add_file_label.sizePolicy().hasHeightForWidth())
        self.add_file_label.setSizePolicy(sizePolicy3)
        font4 = QFont()
        font4.setPointSize(14)
        font4.setBold(True)
        self.add_file_label.setFont(font4)

        self.add_file_h_layout.addWidget(self.add_file_label)

        self.horizontalSpacer_6 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.add_file_h_layout.addItem(self.horizontalSpacer_6)


        self.upload_box_v_box_layout.addLayout(self.add_file_h_layout)

        self.uploadArea = QFrame(self.card)
        self.uploadArea.setObjectName(u"uploadArea")
        sizePolicy.setHeightForWidth(self.uploadArea.sizePolicy().hasHeightForWidth())
        self.uploadArea.setSizePolicy(sizePolicy)
        self.uploadArea.setMinimumSize(QSize(0, 150))
        self.uploadArea.setMaximumSize(QSize(16777215, 120))
        self.uploadArea.setAcceptDrops(True)
        self.uploadArea.setAutoFillBackground(False)
        self.uploadArea.setStyleSheet(u"")
        self.uploadLayout = QVBoxLayout(self.uploadArea)
        self.uploadLayout.setSpacing(14)
        self.uploadLayout.setObjectName(u"uploadLayout")
        self.uploadLayout.setContentsMargins(-1, 9, -1, -1)
        self.upload_area_empty_frame = QFrame(self.uploadArea)
        self.upload_area_empty_frame.setObjectName(u"upload_area_empty_frame")
        self.upload_area_empty_frame.setAcceptDrops(False)
        self.upload_area_empty_v_box = QVBoxLayout(self.upload_area_empty_frame)
        self.upload_area_empty_v_box.setSpacing(0)
        self.upload_area_empty_v_box.setObjectName(u"upload_area_empty_v_box")
        self.upload_area_empty_v_box.setContentsMargins(0, 0, 0, 0)
        self.uploadIcon = QLabel(self.upload_area_empty_frame)
        self.uploadIcon.setObjectName(u"uploadIcon")
        sizePolicy1.setHeightForWidth(self.uploadIcon.sizePolicy().hasHeightForWidth())
        self.uploadIcon.setSizePolicy(sizePolicy1)
        self.uploadIcon.setAutoFillBackground(False)
        self.uploadIcon.setStyleSheet(u"")
        self.uploadIcon.setPixmap(QPixmap(u":/icons/icons/upload.png"))
        self.uploadIcon.setScaledContents(False)
        self.uploadIcon.setAlignment(Qt.AlignCenter)

        self.upload_area_empty_v_box.addWidget(self.uploadIcon)

        self.uploadText = QLabel(self.upload_area_empty_frame)
        self.uploadText.setObjectName(u"uploadText")
        sizePolicy1.setHeightForWidth(self.uploadText.sizePolicy().hasHeightForWidth())
        self.uploadText.setSizePolicy(sizePolicy1)
        self.uploadText.setAlignment(Qt.AlignCenter)

        self.upload_area_empty_v_box.addWidget(self.uploadText)

        self.uploadSupported = QLabel(self.upload_area_empty_frame)
        self.uploadSupported.setObjectName(u"uploadSupported")
        sizePolicy1.setHeightForWidth(self.uploadSupported.sizePolicy().hasHeightForWidth())
        self.uploadSupported.setSizePolicy(sizePolicy1)
        self.uploadSupported.setStyleSheet(u"QLabel { color: rgba(255,255,255,0.72); font-size:11px; }")
        self.uploadSupported.setAlignment(Qt.AlignCenter)
        self.uploadSupported.setMargin(0)

        self.upload_area_empty_v_box.addWidget(self.uploadSupported)


        self.uploadLayout.addWidget(self.upload_area_empty_frame)


        self.upload_box_v_box_layout.addWidget(self.uploadArea)


        self.cardLayout.addLayout(self.upload_box_v_box_layout)

        self.url_loader_qframe = QFrame(self.card)
        self.url_loader_qframe.setObjectName(u"url_loader_qframe")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.url_loader_qframe.sizePolicy().hasHeightForWidth())
        self.url_loader_qframe.setSizePolicy(sizePolicy4)
        self.url_loader_qframe.setMinimumSize(QSize(0, 0))
        self.url_loader_qframe.setMaximumSize(QSize(16777215, 130))
        self.url_loader_qframe.setFrameShape(QFrame.NoFrame)
        self.verticalLayout_2 = QVBoxLayout(self.url_loader_qframe)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(3, -1, 3, -1)
        self.url_loader_lable_Hbox = QHBoxLayout()
        self.url_loader_lable_Hbox.setSpacing(6)
        self.url_loader_lable_Hbox.setObjectName(u"url_loader_lable_Hbox")
        self.url_loader_lable_Hbox.setSizeConstraint(QLayout.SetDefaultConstraint)
        self.icon_label = QLabel(self.url_loader_qframe)
        self.icon_label.setObjectName(u"icon_label")
        sizePolicy2.setHeightForWidth(self.icon_label.sizePolicy().hasHeightForWidth())
        self.icon_label.setSizePolicy(sizePolicy2)
        self.icon_label.setPixmap(QPixmap(u":/icons/icons/link.png"))

        self.url_loader_lable_Hbox.addWidget(self.icon_label)

        self.url_loader_text_label = QLabel(self.url_loader_qframe)
        self.url_loader_text_label.setObjectName(u"url_loader_text_label")
        self.url_loader_text_label.setEnabled(True)
        sizePolicy4.setHeightForWidth(self.url_loader_text_label.sizePolicy().hasHeightForWidth())
        self.url_loader_text_label.setSizePolicy(sizePolicy4)
        self.url_loader_text_label.setFont(font4)

        self.url_loader_lable_Hbox.addWidget(self.url_loader_text_label)

        self.horizontalSpacer_4 = QSpacerItem(40, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.url_loader_lable_Hbox.addItem(self.horizontalSpacer_4)


        self.verticalLayout_2.addLayout(self.url_loader_lable_Hbox)

        self.urlLayout = QHBoxLayout()
        self.urlLayout.setSpacing(9)
        self.urlLayout.setObjectName(u"urlLayout")
        self.urlLayout.setSizeConstraint(QLayout.SetDefaultConstraint)
        self.urlInput = QLineEdit(self.url_loader_qframe)
        self.urlInput.setObjectName(u"urlInput")
        self.urlInput.setMinimumSize(QSize(0, 38))
        font5 = QFont()
        font5.setPointSize(12)
        self.urlInput.setFont(font5)

        self.urlLayout.addWidget(self.urlInput)

        self.loadUrlButton = QPushButton(self.url_loader_qframe)
        self.loadUrlButton.setObjectName(u"loadUrlButton")
        sizePolicy1.setHeightForWidth(self.loadUrlButton.sizePolicy().hasHeightForWidth())
        self.loadUrlButton.setSizePolicy(sizePolicy1)
        self.loadUrlButton.setMinimumSize(QSize(92, 42))
        font6 = QFont()
        font6.setPointSize(10)
        font6.setBold(True)
        font6.setKerning(True)
        self.loadUrlButton.setFont(font6)
        self.loadUrlButton.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.urlLayout.addWidget(self.loadUrlButton)


        self.verticalLayout_2.addLayout(self.urlLayout)

        self.url_helper_text_label = QLabel(self.url_loader_qframe)
        self.url_helper_text_label.setObjectName(u"url_helper_text_label")
        sizePolicy2.setHeightForWidth(self.url_helper_text_label.sizePolicy().hasHeightForWidth())
        self.url_helper_text_label.setSizePolicy(sizePolicy2)
        self.url_helper_text_label.setBaseSize(QSize(0, 0))
        font7 = QFont()
        font7.setPointSize(7)
        font7.setItalic(True)
        font7.setStrikeOut(False)
        font7.setKerning(True)
        self.url_helper_text_label.setFont(font7)

        self.verticalLayout_2.addWidget(self.url_helper_text_label)


        self.cardLayout.addWidget(self.url_loader_qframe)

        self.autoFrame = QFrame(self.card)
        self.autoFrame.setObjectName(u"autoFrame")
        sizePolicy2.setHeightForWidth(self.autoFrame.sizePolicy().hasHeightForWidth())
        self.autoFrame.setSizePolicy(sizePolicy2)
        self.autoFrame.setFrameShape(QFrame.NoFrame)
        self.autoLayout = QVBoxLayout(self.autoFrame)
        self.autoLayout.setSpacing(0)
        self.autoLayout.setObjectName(u"autoLayout")
        self.autoLayout.setSizeConstraint(QLayout.SetDefaultConstraint)
        self.autoLayout.setContentsMargins(3, 6, 3, 0)
        self.autoTopLayout = QHBoxLayout()
        self.autoTopLayout.setSpacing(0)
        self.autoTopLayout.setObjectName(u"autoTopLayout")
        self.autoTopLayout.setContentsMargins(-1, -1, -1, 5)
        self.auto_change_icon_lable = QLabel(self.autoFrame)
        self.auto_change_icon_lable.setObjectName(u"auto_change_icon_lable")
        font8 = QFont()
        font8.setBold(False)
        self.auto_change_icon_lable.setFont(font8)
        self.auto_change_icon_lable.setPixmap(QPixmap(u":/icons/icons/timer.png"))
        self.auto_change_icon_lable.setScaledContents(False)

        self.autoTopLayout.addWidget(self.auto_change_icon_lable)

        self.autoLabel = QLabel(self.autoFrame)
        self.autoLabel.setObjectName(u"autoLabel")
        sizePolicy5 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding)
        sizePolicy5.setHorizontalStretch(0)
        sizePolicy5.setVerticalStretch(0)
        sizePolicy5.setHeightForWidth(self.autoLabel.sizePolicy().hasHeightForWidth())
        self.autoLabel.setSizePolicy(sizePolicy5)
        self.autoLabel.setFont(font4)

        self.autoTopLayout.addWidget(self.autoLabel)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.autoTopLayout.addItem(self.horizontalSpacer_2)

        self.enabledCheck = QCheckBox(self.autoFrame)
        self.enabledCheck.setObjectName(u"enabledCheck")
        font9 = QFont()
        font9.setPointSize(13)
        self.enabledCheck.setFont(font9)
        self.enabledCheck.setChecked(True)

        self.autoTopLayout.addWidget(self.enabledCheck)


        self.autoLayout.addLayout(self.autoTopLayout)


        self.cardLayout.addWidget(self.autoFrame)

        self.source_n_interval_frame = QFrame(self.card)
        self.source_n_interval_frame.setObjectName(u"source_n_interval_frame")
        sizePolicy.setHeightForWidth(self.source_n_interval_frame.sizePolicy().hasHeightForWidth())
        self.source_n_interval_frame.setSizePolicy(sizePolicy)
        self.source_n_interval_frame.setMinimumSize(QSize(0, 85))
        font10 = QFont()
        font10.setKerning(True)
        self.source_n_interval_frame.setFont(font10)
        self.source_n_interval_frame.setFrameShape(QFrame.NoFrame)
        self.horizontalLayout_5 = QHBoxLayout(self.source_n_interval_frame)
        self.horizontalLayout_5.setSpacing(6)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.horizontalLayout_5.setContentsMargins(3, 6, 3, 3)
        self.interval_v_layout = QVBoxLayout()
        self.interval_v_layout.setSpacing(3)
        self.interval_v_layout.setObjectName(u"interval_v_layout")
        self.interval_v_layout.setContentsMargins(-1, -1, -1, 0)
        self.inverval_lable = QLabel(self.source_n_interval_frame)
        self.inverval_lable.setObjectName(u"inverval_lable")
        font11 = QFont()
        font11.setPointSize(13)
        font11.setBold(True)
        self.inverval_lable.setFont(font11)

        self.interval_v_layout.addWidget(self.inverval_lable)

        self.interval_spinBox = QSpinBox(self.source_n_interval_frame)
        self.interval_spinBox.setObjectName(u"interval_spinBox")
        self.interval_spinBox.setMinimumSize(QSize(0, 35))
        self.interval_spinBox.setFont(font)
        self.interval_spinBox.setWrapping(False)
        self.interval_spinBox.setFrame(False)
        self.interval_spinBox.setReadOnly(False)
        self.interval_spinBox.setMinimum(1)
        self.interval_spinBox.setMaximum(999)
        self.interval_spinBox.setSingleStep(1)

        self.interval_v_layout.addWidget(self.interval_spinBox)


        self.horizontalLayout_5.addLayout(self.interval_v_layout)

        self.source_v_layout = QVBoxLayout()
        self.source_v_layout.setSpacing(9)
        self.source_v_layout.setObjectName(u"source_v_layout")
        self.source_v_layout.setContentsMargins(-1, -1, -1, 0)
        self.wallpaper_source_lable = QLabel(self.source_n_interval_frame)
        self.wallpaper_source_lable.setObjectName(u"wallpaper_source_lable")
        self.wallpaper_source_lable.setFont(font11)

        self.source_v_layout.addWidget(self.wallpaper_source_lable)

        self.source_inner_h_loyout = QHBoxLayout()
        self.source_inner_h_loyout.setObjectName(u"source_inner_h_loyout")
        self.super_wallpaper_btn = QPushButton(self.source_n_interval_frame)
        self.super_wallpaper_btn.setObjectName(u"super_wallpaper_btn")
        self.super_wallpaper_btn.setFont(font3)
        self.super_wallpaper_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.super_wallpaper_btn.setLayoutDirection(Qt.LeftToRight)
        icon2 = QIcon()
        icon2.addFile(u":/icons/icons/sparkles.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.super_wallpaper_btn.setIcon(icon2)
        self.super_wallpaper_btn.setIconSize(QSize(20, 20))

        self.source_inner_h_loyout.addWidget(self.super_wallpaper_btn)

        self.fvrt_wallpapers_btn = QPushButton(self.source_n_interval_frame)
        self.fvrt_wallpapers_btn.setObjectName(u"fvrt_wallpapers_btn")
        self.fvrt_wallpapers_btn.setFont(font)
        self.fvrt_wallpapers_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon3 = QIcon()
        icon3.addFile(u":/icons/icons/heart.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.fvrt_wallpapers_btn.setIcon(icon3)
        self.fvrt_wallpapers_btn.setIconSize(QSize(20, 20))

        self.source_inner_h_loyout.addWidget(self.fvrt_wallpapers_btn)

        self.added_wallpaper_btn = QPushButton(self.source_n_interval_frame)
        self.added_wallpaper_btn.setObjectName(u"added_wallpaper_btn")
        self.added_wallpaper_btn.setFont(font)
        self.added_wallpaper_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon4 = QIcon()
        icon4.addFile(u":/icons/icons/circle_plus.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.added_wallpaper_btn.setIcon(icon4)
        self.added_wallpaper_btn.setIconSize(QSize(20, 20))

        self.source_inner_h_loyout.addWidget(self.added_wallpaper_btn)


        self.source_v_layout.addLayout(self.source_inner_h_loyout)


        self.horizontalLayout_5.addLayout(self.source_v_layout)


        self.cardLayout.addWidget(self.source_n_interval_frame)

        self.range_frame = QFrame(self.card)
        self.range_frame.setObjectName(u"range_frame")
        sizePolicy6 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        sizePolicy6.setHorizontalStretch(0)
        sizePolicy6.setVerticalStretch(0)
        sizePolicy6.setHeightForWidth(self.range_frame.sizePolicy().hasHeightForWidth())
        self.range_frame.setSizePolicy(sizePolicy6)
        self.range_frame.setMinimumSize(QSize(0, 90))
        self.range_frame.setFrameShape(QFrame.NoFrame)
        self.horizontalLayout_6 = QHBoxLayout(self.range_frame)
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.horizontalLayout_6.setContentsMargins(3, 0, 3, -1)
        self.range_v_layout = QVBoxLayout()
        self.range_v_layout.setSpacing(0)
        self.range_v_layout.setObjectName(u"range_v_layout")
        self.range_lable = QLabel(self.range_frame)
        self.range_lable.setObjectName(u"range_lable")
        self.range_lable.setMinimumSize(QSize(0, 0))
        self.range_lable.setFont(font11)
        self.range_lable.setStyleSheet(u"")

        self.range_v_layout.addWidget(self.range_lable)

        self.range_inner_h_layout = QHBoxLayout()
        self.range_inner_h_layout.setSpacing(6)
        self.range_inner_h_layout.setObjectName(u"range_inner_h_layout")
        self.range_all_bnt = QPushButton(self.range_frame)
        self.range_all_bnt.setObjectName(u"range_all_bnt")
        self.range_all_bnt.setFont(font3)
        self.range_all_bnt.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon5 = QIcon()
        icon5.addFile(u":/icons/icons/wallpaper.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.range_all_bnt.setIcon(icon5)
        self.range_all_bnt.setIconSize(QSize(20, 20))

        self.range_inner_h_layout.addWidget(self.range_all_bnt)

        self.range_wallpaper_bnt = QPushButton(self.range_frame)
        self.range_wallpaper_bnt.setObjectName(u"range_wallpaper_bnt")
        self.range_wallpaper_bnt.setFont(font)
        self.range_wallpaper_bnt.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        icon6 = QIcon()
        icon6.addFile(u":/icons/icons/film.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.range_wallpaper_bnt.setIcon(icon6)
        self.range_wallpaper_bnt.setIconSize(QSize(20, 20))

        self.range_inner_h_layout.addWidget(self.range_wallpaper_bnt)

        self.range_mp4_bnt = QPushButton(self.range_frame)
        self.range_mp4_bnt.setObjectName(u"range_mp4_bnt")
        self.range_mp4_bnt.setFont(font)
        self.range_mp4_bnt.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.range_mp4_bnt.setIcon(icon6)
        self.range_mp4_bnt.setIconSize(QSize(20, 20))

        self.range_inner_h_layout.addWidget(self.range_mp4_bnt)

        self.horizontalSpacer_5 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.range_inner_h_layout.addItem(self.horizontalSpacer_5)


        self.range_v_layout.addLayout(self.range_inner_h_layout)


        self.horizontalLayout_6.addLayout(self.range_v_layout)


        self.cardLayout.addWidget(self.range_frame)

        self.bottomFrame = QFrame(self.card)
        self.bottomFrame.setObjectName(u"bottomFrame")
        sizePolicy.setHeightForWidth(self.bottomFrame.sizePolicy().hasHeightForWidth())
        self.bottomFrame.setSizePolicy(sizePolicy)
        self.bottomFrame.setMinimumSize(QSize(0, 80))
        self.bottomFrame.setMaximumSize(QSize(16777215, 16777215))
        self.bottomLayout = QHBoxLayout(self.bottomFrame)
        self.bottomLayout.setObjectName(u"bottomLayout")
        self.statusLabel = QLabel(self.bottomFrame)
        self.statusLabel.setObjectName(u"statusLabel")
        self.statusLabel.setSizeIncrement(QSize(0, 0))
        font12 = QFont()
        font12.setPointSize(9)
        font12.setBold(True)
        self.statusLabel.setFont(font12)

        self.bottomLayout.addWidget(self.statusLabel)

        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.bottomLayout.addItem(self.horizontalSpacer_3)

        self.startButton = QPushButton(self.bottomFrame)
        self.startButton.setObjectName(u"startButton")
        self.startButton.setMinimumSize(QSize(110, 40))
        font13 = QFont()
        font13.setPointSize(10)
        font13.setBold(False)
        self.startButton.setFont(font13)
        self.startButton.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.bottomLayout.addWidget(self.startButton)

        self.resetButton = QPushButton(self.bottomFrame)
        self.resetButton.setObjectName(u"resetButton")
        self.resetButton.setMinimumSize(QSize(110, 40))
        self.resetButton.setFont(font13)
        self.resetButton.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.bottomLayout.addWidget(self.resetButton)


        self.cardLayout.addWidget(self.bottomFrame)


        self.verticalLayout.addWidget(self.card)

        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        self.urlInput.returnPressed.connect(self.loadUrlButton.click)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Tapeciarnia", None))
        self.logoLabel.setText("")
        self.emailInput.setPlaceholderText(QCoreApplication.translate("MainWindow", u"email", None))
        self.passwordInput.setPlaceholderText(QCoreApplication.translate("MainWindow", u"password", None))
#if QT_CONFIG(tooltip)
        self.logInBnt.setToolTip(QCoreApplication.translate("MainWindow", u"Sign in", None))
#endif // QT_CONFIG(tooltip)
        self.logInBnt.setText(QCoreApplication.translate("MainWindow", u"Log In", None))
        self.logInBnt.setProperty(u"class", QCoreApplication.translate("MainWindow", u"primary", None))
        self.language_icon.setText("")
        self.langCombo.setItemText(0, QCoreApplication.translate("MainWindow", u"EN", None))
        self.langCombo.setItemText(1, QCoreApplication.translate("MainWindow", u"PL", None))
        self.langCombo.setItemText(2, QCoreApplication.translate("MainWindow", u"DE", None))

        self.randomAnimButton.setText(QCoreApplication.translate("MainWindow", u"  Shuffle animated", None))
        self.randomAnimButton.setProperty(u"class", QCoreApplication.translate("MainWindow", u"ghost", None))
        self.randomAnimButton.setProperty(u"icon_name", QCoreApplication.translate("MainWindow", u"shuffle", None))
        self.randomButton.setText(QCoreApplication.translate("MainWindow", u"  Shuffle wallpaper", None))
        self.randomButton.setProperty(u"class", QCoreApplication.translate("MainWindow", u"ghost", None))
        self.randomButton.setProperty(u"icon_name", QCoreApplication.translate("MainWindow", u"shuffle", None))
        self.browseButton.setText(QCoreApplication.translate("MainWindow", u"  Browse wallpapers", None))
        self.browseButton.setProperty(u"class", QCoreApplication.translate("MainWindow", u"primary", None))
        self.browseButton.setProperty(u"icon_name", QCoreApplication.translate("MainWindow", u"images", None))
        self.add_files_icon.setText("")
        self.add_file_label.setText(QCoreApplication.translate("MainWindow", u"Add files", None))
        self.add_file_label.setProperty(u"class", QCoreApplication.translate("MainWindow", u"MainUILable", None))
        self.uploadIcon.setText("")
        self.uploadText.setText(QCoreApplication.translate("MainWindow", u"Drag & drop a photo or video here, or click to choose a file", None))
        self.uploadText.setProperty(u"class", QCoreApplication.translate("MainWindow", u"MainUILable", None))
        self.uploadSupported.setText(QCoreApplication.translate("MainWindow", u"Supported: JPG, PNG, MP4", None))
        self.uploadSupported.setProperty(u"class", QCoreApplication.translate("MainWindow", u"MainUILable", None))
        self.icon_label.setText("")
        self.url_loader_text_label.setText(QCoreApplication.translate("MainWindow", u"Images or Video URL", None))
        self.url_loader_text_label.setProperty(u"class", QCoreApplication.translate("MainWindow", u"MainUILable", None))
        self.urlInput.setPlaceholderText(QCoreApplication.translate("MainWindow", u"https://example.com/image.jpg or https://.../video.mp4", None))
        self.loadUrlButton.setText(QCoreApplication.translate("MainWindow", u"Load", None))
        self.loadUrlButton.setProperty(u"class", QCoreApplication.translate("MainWindow", u"primary", None))
        self.url_helper_text_label.setText(QCoreApplication.translate("MainWindow", u"Paete a dirick link to a .jpg/.png or mp4", None))
        self.url_helper_text_label.setProperty(u"class", QCoreApplication.translate("MainWindow", u"MainUILable", None))
        self.auto_change_icon_lable.setText("")
        self.autoLabel.setText(QCoreApplication.translate("MainWindow", u"Automatic wallpaper change", None))
        self.autoLabel.setProperty(u"class", QCoreApplication.translate("MainWindow", u"MainUILable", None))
        self.enabledCheck.setText(QCoreApplication.translate("MainWindow", u"Enabled", None))
        self.inverval_lable.setText(QCoreApplication.translate("MainWindow", u"Interval (minutes)", None))
        self.inverval_lable.setProperty(u"class", QCoreApplication.translate("MainWindow", u"MainUILable", None))
        self.wallpaper_source_lable.setText(QCoreApplication.translate("MainWindow", u"Wallpaper source", None))
        self.wallpaper_source_lable.setProperty(u"class", QCoreApplication.translate("MainWindow", u"MainUILable", None))
        self.super_wallpaper_btn.setText(QCoreApplication.translate("MainWindow", u"  Super Wallpaper", None))
        self.super_wallpaper_btn.setProperty(u"class", QCoreApplication.translate("MainWindow", u"ghost", None))
        self.super_wallpaper_btn.setProperty(u"icon_name", QCoreApplication.translate("MainWindow", u"sparkles", None))
        self.fvrt_wallpapers_btn.setText(QCoreApplication.translate("MainWindow", u"  Favorite Wallpapers", None))
        self.fvrt_wallpapers_btn.setProperty(u"class", QCoreApplication.translate("MainWindow", u"ghost", None))
        self.fvrt_wallpapers_btn.setProperty(u"icon_name", QCoreApplication.translate("MainWindow", u"heart", None))
        self.added_wallpaper_btn.setText(QCoreApplication.translate("MainWindow", u"  Added wallpapers", None))
        self.added_wallpaper_btn.setProperty(u"class", QCoreApplication.translate("MainWindow", u"ghost", None))
        self.added_wallpaper_btn.setProperty(u"icon_name", QCoreApplication.translate("MainWindow", u"circle_plus", None))
        self.range_lable.setText(QCoreApplication.translate("MainWindow", u"Range", None))
        self.range_lable.setProperty(u"class", QCoreApplication.translate("MainWindow", u"MainUILable", None))
        self.range_all_bnt.setText(QCoreApplication.translate("MainWindow", u"  All", None))
        self.range_all_bnt.setProperty(u"class", QCoreApplication.translate("MainWindow", u"ghost", None))
        self.range_all_bnt.setProperty(u"icon_name", QCoreApplication.translate("MainWindow", u"wallpaper", None))
        self.range_wallpaper_bnt.setText(QCoreApplication.translate("MainWindow", u"  Wallpaper", None))
        self.range_wallpaper_bnt.setProperty(u"class", QCoreApplication.translate("MainWindow", u"ghost", None))
        self.range_wallpaper_bnt.setProperty(u"icon_name", QCoreApplication.translate("MainWindow", u"film", None))
        self.range_mp4_bnt.setText(QCoreApplication.translate("MainWindow", u"  Mp4", None))
        self.range_mp4_bnt.setProperty(u"class", QCoreApplication.translate("MainWindow", u"ghost", None))
        self.range_mp4_bnt.setProperty(u"icon_name", QCoreApplication.translate("MainWindow", u"film", None))
        self.statusLabel.setText(QCoreApplication.translate("MainWindow", u"", None))
        self.startButton.setText(QCoreApplication.translate("MainWindow", u"Start", None))
        self.startButton.setProperty(u"class", QCoreApplication.translate("MainWindow", u"ghost", None))
        self.resetButton.setText(QCoreApplication.translate("MainWindow", u"Reset", None))
        self.resetButton.setProperty(u"class", QCoreApplication.translate("MainWindow", u"ghost", None))
    # retranslateUi

