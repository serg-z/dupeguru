# Copyright 2016 Hardcoded Software (http://www.hardcoded.net)
#
# This software is licensed under the "GPLv3" License as described in the "LICENSE" file,
# which should be included with this package. The terms are also available at
# http://www.gnu.org/licenses/gpl-3.0.html

from PyQt5.QtCore import QRect, Qt
from PyQt5.QtWidgets import (
    QWidget,
    QFileDialog,
    QHeaderView,
    QVBoxLayout,
    QHBoxLayout,
    QTreeView,
    QAbstractItemView,
    QSpacerItem,
    QSizePolicy,
    QPushButton,
    QMainWindow,
    QMenuBar,
    QMenu,
    QLabel,
    QComboBox,
)
from PyQt5.QtGui import QPixmap, QIcon

from hscommon.trans import trget
from core.app import AppMode
from qtlib.radio_box import RadioBox
from qtlib.recent import Recent
from qtlib.util import moveToScreenCenter, createActions

from . import platform
from .directories_model import DirectoriesModel, DirectoriesDelegate

tr = trget("ui")


class DirectoriesDialog(QMainWindow):
    def __init__(self, app, **kwargs):
        super().__init__(None, **kwargs)
        self.app = app
        self.lastAddedFolder = platform.INITIAL_FOLDER_IN_DIALOGS
        self.recentFolders = Recent(self.app, "recentFolders")
        self._setupUi()
        self._updateScanTypeList()
        self.directoriesModel = DirectoriesModel(
            self.app.model.directory_tree, view=self.treeView
        )
        self.directoriesDelegate = DirectoriesDelegate()
        self.treeView.setItemDelegate(self.directoriesDelegate)
        self._setupColumns()
        self.app.recentResults.addMenu(self.menuLoadRecent)
        self.app.recentResults.addMenu(self.menuRecentResults)
        self.recentFolders.addMenu(self.menuRecentFolders)
        self._updateAddButton()
        self._updateRemoveButton()
        self._updateLoadResultsButton()
        self._updateActionsState()
        self._setupBindings()

    def _setupBindings(self):
        self.appModeRadioBox.itemSelected.connect(self.appModeButtonSelected)
        self.showPreferencesButton.clicked.connect(self.app.actionPreferences.trigger)
        self.scanButton.clicked.connect(self.scanButtonClicked)
        self.loadResultsButton.clicked.connect(self.actionLoadResults.trigger)
        self.addFolderButton.clicked.connect(self.actionAddFolder.trigger)
        self.removeFolderButton.clicked.connect(self.removeFolderButtonClicked)
        self.treeView.selectionModel().selectionChanged.connect(self.selectionChanged)
        self.app.recentResults.itemsChanged.connect(self._updateLoadResultsButton)
        self.recentFolders.itemsChanged.connect(self._updateAddButton)
        self.recentFolders.mustOpenItem.connect(self.app.model.add_directory)
        self.directoriesModel.foldersAdded.connect(self.directoriesModelAddedFolders)
        self.app.willSavePrefs.connect(self.appWillSavePrefs)

    def _setupActions(self):
        # (name, shortcut, icon, desc, func)
        ACTIONS = [
            (
                "actionLoadResults",
                "Ctrl+L",
                "",
                tr("Load Results..."),
                self.loadResultsTriggered,
            ),
            (
                "actionShowResultsWindow",
                "",
                "",
                tr("Results Window"),
                self.app.showResultsWindow,
            ),
            ("actionAddFolder", "", "", tr("Add Folder..."), self.addFolderTriggered),
        ]
        createActions(ACTIONS, self)

    def _setupMenu(self):
        self.menubar = QMenuBar(self)
        self.menubar.setGeometry(QRect(0, 0, 42, 22))
        self.menuFile = QMenu(self.menubar)
        self.menuFile.setTitle(tr("File"))
        self.menuView = QMenu(self.menubar)
        self.menuView.setTitle(tr("View"))
        self.menuHelp = QMenu(self.menubar)
        self.menuHelp.setTitle(tr("Help"))
        self.menuLoadRecent = QMenu(self.menuFile)
        self.menuLoadRecent.setTitle(tr("Load Recent Results"))
        self.setMenuBar(self.menubar)

        self.menuFile.addAction(self.actionLoadResults)
        self.menuFile.addAction(self.menuLoadRecent.menuAction())
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.app.actionClearPictureCache)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.app.actionQuit)
        self.menuView.addAction(self.app.actionPreferences)
        self.menuView.addAction(self.actionShowResultsWindow)
        self.menuView.addAction(self.app.actionIgnoreList)
        self.menuHelp.addAction(self.app.actionShowHelp)
        self.menuHelp.addAction(self.app.actionOpenDebugLog)
        self.menuHelp.addAction(self.app.actionAbout)

        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuView.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())

        # Recent folders menu
        self.menuRecentFolders = QMenu()
        self.menuRecentFolders.addAction(self.actionAddFolder)
        self.menuRecentFolders.addSeparator()

        # Recent results menu
        self.menuRecentResults = QMenu()
        self.menuRecentResults.addAction(self.actionLoadResults)
        self.menuRecentResults.addSeparator()

    def _setupUi(self):
        self.setWindowTitle(self.app.NAME)
        self.resize(420, 338)
        self.centralwidget = QWidget(self)
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        hl = QHBoxLayout()
        label = QLabel(tr("Application Mode:"), self)
        label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        hl.addWidget(label)
        self.appModeRadioBox = RadioBox(
            self, items=[tr("Standard"), tr("Music"), tr("Picture")], spread=False
        )
        hl.addWidget(self.appModeRadioBox)
        self.verticalLayout.addLayout(hl)
        hl = QHBoxLayout()
        hl.setAlignment(Qt.AlignLeft)
        label = QLabel(tr("Scan Type:"), self)
        label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        hl.addWidget(label)
        self.scanTypeComboBox = QComboBox(self)
        self.scanTypeComboBox.setSizePolicy(
            QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        )
        self.scanTypeComboBox.setMaximumWidth(400)
        hl.addWidget(self.scanTypeComboBox)
        self.showPreferencesButton = QPushButton(tr("More Options"), self.centralwidget)
        self.showPreferencesButton.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        hl.addWidget(self.showPreferencesButton)
        self.verticalLayout.addLayout(hl)
        self.promptLabel = QLabel(
            tr('Select folders to scan and press "Scan".'), self.centralwidget
        )
        self.verticalLayout.addWidget(self.promptLabel)
        self.treeView = QTreeView(self.centralwidget)
        self.treeView.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.treeView.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.treeView.setAcceptDrops(True)
        triggers = (
            QAbstractItemView.DoubleClicked
            | QAbstractItemView.EditKeyPressed
            | QAbstractItemView.SelectedClicked
        )
        self.treeView.setEditTriggers(triggers)
        self.treeView.setDragDropOverwriteMode(True)
        self.treeView.setDragDropMode(QAbstractItemView.DropOnly)
        self.treeView.setUniformRowHeights(True)
        self.verticalLayout.addWidget(self.treeView)
        self.horizontalLayout = QHBoxLayout()
        self.removeFolderButton = QPushButton(self.centralwidget)
        self.removeFolderButton.setIcon(QIcon(QPixmap(":/minus")))
        self.removeFolderButton.setShortcut("Del")
        self.horizontalLayout.addWidget(self.removeFolderButton)
        self.addFolderButton = QPushButton(self.centralwidget)
        self.addFolderButton.setIcon(QIcon(QPixmap(":/plus")))
        self.horizontalLayout.addWidget(self.addFolderButton)
        spacerItem1 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem1)
        self.loadResultsButton = QPushButton(self.centralwidget)
        self.loadResultsButton.setText(tr("Load Results"))
        self.horizontalLayout.addWidget(self.loadResultsButton)
        self.scanButton = QPushButton(self.centralwidget)
        self.scanButton.setText(tr("Scan"))
        self.scanButton.setDefault(True)
        self.horizontalLayout.addWidget(self.scanButton)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.setCentralWidget(self.centralwidget)

        self._setupActions()
        self._setupMenu()

        if self.app.prefs.directoriesWindowRect is not None:
            self.setGeometry(self.app.prefs.directoriesWindowRect)

    def _setupColumns(self):
        header = self.treeView.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.resizeSection(1, 100)

    def _updateActionsState(self):
        self.actionShowResultsWindow.setEnabled(self.app.resultWindow is not None)

    def _updateAddButton(self):
        if self.recentFolders.isEmpty():
            self.addFolderButton.setMenu(None)
        else:
            self.addFolderButton.setMenu(self.menuRecentFolders)

    def _updateRemoveButton(self):
        indexes = self.treeView.selectedIndexes()
        if not indexes:
            self.removeFolderButton.setEnabled(False)
            return
        self.removeFolderButton.setEnabled(True)

    def _updateLoadResultsButton(self):
        if self.app.recentResults.isEmpty():
            self.loadResultsButton.setMenu(None)
        else:
            self.loadResultsButton.setMenu(self.menuRecentResults)

    def _updateScanTypeList(self):
        try:
            self.scanTypeComboBox.currentIndexChanged[int].disconnect(
                self.scanTypeChanged
            )
        except TypeError:
            # Not connected, ignore
            pass
        self.scanTypeComboBox.clear()
        scan_options = self.app.model.SCANNER_CLASS.get_scan_options()
        for scan_option in scan_options:
            self.scanTypeComboBox.addItem(scan_option.label)
        SCAN_TYPE_ORDER = [so.scan_type for so in scan_options]
        selected_scan_type = self.app.prefs.get_scan_type(self.app.model.app_mode)
        scan_type_index = SCAN_TYPE_ORDER.index(selected_scan_type)
        self.scanTypeComboBox.setCurrentIndex(scan_type_index)
        self.scanTypeComboBox.currentIndexChanged[int].connect(self.scanTypeChanged)
        self.app._update_options()

    # --- QWidget overrides
    def closeEvent(self, event):
        event.accept()
        if self.app.model.results.is_modified:
            title = tr("Unsaved results")
            msg = tr("You have unsaved results, do you really want to quit?")
            if not self.app.confirm(title, msg):
                event.ignore()
        if event.isAccepted():
            self.app.shutdown()

    # --- Events
    def addFolderTriggered(self):
        title = tr("Select a folder to add to the scanning list")
        flags = QFileDialog.ShowDirsOnly
        dirpath = str(
            QFileDialog.getExistingDirectory(self, title, self.lastAddedFolder, flags)
        )
        if not dirpath:
            return
        self.lastAddedFolder = dirpath
        self.app.model.add_directory(dirpath)
        self.recentFolders.insertItem(dirpath)

    def appModeButtonSelected(self, index):
        if index == 2:
            mode = AppMode.Picture
        elif index == 1:
            mode = AppMode.Music
        else:
            mode = AppMode.Standard
        self.app.model.app_mode = mode
        self._updateScanTypeList()

    def appWillSavePrefs(self):
        self.app.prefs.directoriesWindowRect = self.geometry()

    def directoriesModelAddedFolders(self, folders):
        for folder in folders:
            self.recentFolders.insertItem(folder)

    def loadResultsTriggered(self):
        title = tr("Select a results file to load")
        files = ";;".join([tr("dupeGuru Results (*.dupeguru)"), tr("All Files (*.*)")])
        destination = QFileDialog.getOpenFileName(self, title, "", files)[0]
        if destination:
            self.app.model.load_from(destination)
            self.app.recentResults.insertItem(destination)

    def removeFolderButtonClicked(self):
        self.directoriesModel.model.remove_selected()

    def scanButtonClicked(self):
        if self.app.model.results.is_modified:
            title = tr("Start a new scan")
            msg = tr("You have unsaved results, do you really want to continue?")
            if not self.app.confirm(title, msg):
                return
        self.app.model.start_scanning()

    def scanTypeChanged(self, index):
        scan_options = self.app.model.SCANNER_CLASS.get_scan_options()
        self.app.prefs.set_scan_type(
            self.app.model.app_mode, scan_options[index].scan_type
        )
        self.app._update_options()

    def selectionChanged(self, selected, deselected):
        self._updateRemoveButton()

    def showEvent(self, event):
        if self.isMaximized() is False:
            # have to do this here as the frameGeometry is not correct until shown
            moveToScreenCenter(self)
        super().showEvent(event)
