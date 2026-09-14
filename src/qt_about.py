"""About and private GitHub updates, independent of simulation workers."""
from datetime import datetime
from pathlib import Path
import threading

from PyQt6.QtCore import Qt, QPointF, QThread, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QDesktopServices, QIcon, QPainter, QPen
from PyQt6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QFileDialog,
    QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
    QProgressBar, QPushButton, QVBoxLayout, QWidget)

from app_version import installation_info
from desktop_runtime import resource_root
from qt_common import COLORS, button, note, theme_manager
from update_client import GitHubUpdateClient, REPOSITORY_URL, UpdateCancelled, UpdateError
from update_credentials import CredentialStore


TOKEN_URL = 'https://github.com/settings/personal-access-tokens/new'
TOKEN_HELP_URL = ('https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/'
                  'managing-your-personal-access-tokens')


def label(text, name='', wrap=False):
    widget = QLabel(str(text))
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(wrap)
    if name:
        widget.setObjectName(name)
    return widget


def plain_note(text):
    widget = note(str(text))
    widget.setTextFormat(Qt.TextFormat.PlainText)
    return widget


def display_time(value):
    """Display a server timestamp locally; never fabricate an update/check date."""
    if not value:
        return 'Never'
    try:
        timestamp = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return timestamp.astimezone().strftime('%b %d, %Y at %I:%M %p %Z')
    except (TypeError, ValueError):
        return 'Not recorded'


class StatusMark(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(46, 46)
        self.kind = 'not_checked'

    def paintEvent(self, event):
        c = COLORS[theme_manager().mode]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(c['hover']))
        painter.drawEllipse(0, 0, 46, 46)
        painter.setPen(QPen(QColor(c['accent']), 2.3, Qt.PenStyle.SolidLine,
                           Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        if self.kind in ('current', 'downloaded'):
            painter.drawLine(QPointF(14, 23), QPointF(20, 29))
            painter.drawLine(QPointF(20, 29), QPointF(33, 16))
        elif self.kind == 'available':
            painter.drawLine(QPointF(23, 31), QPointF(23, 15))
            painter.drawLine(QPointF(16, 22), QPointF(23, 15))
            painter.drawLine(QPointF(30, 22), QPointF(23, 15))
        else:
            painter.drawEllipse(14, 14, 18, 18)
            painter.drawLine(QPointF(23, 18), QPointF(23, 24))
            painter.drawLine(QPointF(23, 24), QPointF(27, 26))
        painter.end()


class ConnectionDialog(QDialog):
    """A token is never copied to the clipboard, logged, or put in app settings."""
    def __init__(self, credential_store, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Connect GitHub')
        self.setMinimumWidth(460)
        self.resize(550, 470)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(15)
        layout.addWidget(label('Connect GitHub', 'sectionTitle'))
        layout.addWidget(plain_note('Use your own GitHub token with read access to '
            'Wgeshow/optical-design-studio-updates. Your account must already have repository access. '
            'The repository owner can create a fine-grained token for only this repository '
            'with Contents: Read-only. Invited collaborators should check GitHub’s token limitations '
            'in the instructions below. Never use a shared account token.'))
        links = QHBoxLayout()
        links.addWidget(button('Create token', lambda: QDesktopServices.openUrl(QUrl(TOKEN_URL))))
        links.addWidget(button('GitHub instructions', lambda: QDesktopServices.openUrl(QUrl(TOKEN_HELP_URL))))
        links.addStretch(1)
        layout.addLayout(links)
        layout.addWidget(plain_note('Personal access token'))
        self.token_edit = QLineEdit()
        self.token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_edit.setPlaceholderText('Paste your personal access token')
        self.token_edit.setAccessibleName('GitHub personal access token')
        layout.addWidget(self.token_edit)
        self.remember = QCheckBox('Remember on this computer')
        self.remember.setChecked(False)
        try:
            can_persist = bool(credential_store.can_persist)
            storage = str(credential_store.storage_label)
        except Exception:
            can_persist, storage = False, 'OS credential storage is unavailable'
        self.remember.setEnabled(can_persist)
        layout.addWidget(self.remember)
        layout.addWidget(plain_note(f'{storage}. Without Remember, access lasts only for this application session. '
            'Credentials are never included in projects or shared data.'))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.connect_button = buttons.addButton('Connect and check', QDialogButtonBox.ButtonRole.AcceptRole)
        self.connect_button.setEnabled(False)
        self.token_edit.textChanged.connect(lambda value: self.connect_button.setEnabled(bool(value.strip())))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def take_credentials(self):
        token = self.token_edit.text().strip()
        remember = self.remember.isEnabled() and self.remember.isChecked()
        self.token_edit.clear()
        return token, remember

    def reject(self):
        self.token_edit.clear()
        super().reject()


class UpdateWorker(QThread):
    progress = pyqtSignal(object, object)

    def __init__(self, client_factory, token, operation, args, parent=None):
        super().__init__(parent)
        self._factory = client_factory
        self._token = token
        self.operation = operation
        self.args = args
        self.cancel_event = threading.Event()
        self.result = None
        self.error = None
        self.cancelled = False

    def cancel(self):
        self.cancel_event.set()

    def run(self):
        try:
            client = self._factory(self._token)
            if self.operation == 'download':
                self.result = client.download(*self.args,
                    progress=lambda done, total: self.progress.emit(done, total), cancel=self.cancel_event)
            else:
                self.result = client.check(*self.args, cancel=self.cancel_event)
        except UpdateCancelled:
            self.cancelled = True
        except UpdateError as exc:
            self.error = str(exc)
        except Exception:
            # Transport exceptions may contain headers, credentials, or signed URLs.
            self.error = 'The update request could not be completed. Please try again.'
        finally:
            self._token = None


class AboutPage(QWidget):
    idle = pyqtSignal()

    def __init__(self, store, client_factory=None, credential_store=None):
        super().__init__()
        self.store = store
        self._client_factory = client_factory or GitHubUpdateClient
        self._credentials = credential_store if credential_store is not None else CredentialStore()
        self._token = None
        self._username = None
        self._worker = None
        self._pending_connection = None
        self._release = None
        self._downloaded_path = None
        self._connection_note = ''
        self.info = installation_info()
        try:
            self._token = self._credentials.load() or None
        except Exception:
            self._connection_note = 'Saved access could not be read. Connect again to check for updates.'
        self._build()
        self._set_state('not_checked' if self._token else 'signin')
        self._refresh_account()
        theme_manager().changed.connect(self.retheme)
        self.retheme()

    @property
    def busy(self):
        # Keep the guard through queued finished handling, not only QThread.run().
        return self._worker is not None

    def _build(self):
        self.setObjectName('page')
        root = QVBoxLayout(self)
        root.setContentsMargins(34, 28, 34, 28)
        root.setSpacing(22)
        titles = QVBoxLayout()
        titles.setSpacing(6)
        titles.addWidget(label('About', 'pageTitle'))
        titles.addWidget(plain_note('Your application version and software updates.'))
        root.addLayout(titles)
        identity = QFrame()
        identity.setObjectName('aboutCard')
        card = QVBoxLayout(identity)
        card.setContentsMargins(26, 26, 26, 24)
        card.setSpacing(22)
        brand = QHBoxLayout()
        brand.setSpacing(18)
        logo = QLabel()
        logo.setPixmap(QIcon(str(resource_root() / 'S4_Studio.ico')).pixmap(68, 68))
        logo.setFixedSize(72, 72)
        brand.addWidget(logo)
        branding = QVBoxLayout()
        branding.setSpacing(7)
        branding.addWidget(label('Optical Design Studio', 'aboutBrand', True))
        branding.addWidget(plain_note('Design, simulate and optimize optical structures.'))
        brand.addLayout(branding, 1)
        card.addLayout(brand)
        line = QFrame()
        line.setObjectName('aboutDivider')
        line.setFixedHeight(1)
        card.addWidget(line)
        metadata = QGridLayout()
        metadata.setHorizontalSpacing(30)
        metadata.setVerticalSpacing(7)
        self.metadata_labels = {}
        for column, (key, value) in enumerate((
            ('Installed version', self.info['version']),
            ('Last updated', self.info['last_updated']),
            ('Platform', self.info['platform']),
        )):
            metadata.setColumnStretch(column, 1)
            metadata.addWidget(plain_note(key), 0, column)
            value_label = label(value, 'aboutValue', True)
            self.metadata_labels[key] = value_label
            metadata.addWidget(value_label, 1, column)
        card.addLayout(metadata)
        root.addWidget(identity)
        self.update_card = QFrame()
        self.update_card.setObjectName('aboutCard')
        update = QVBoxLayout(self.update_card)
        update.setContentsMargins(26, 24, 26, 24)
        update.setSpacing(21)
        top = QHBoxLayout()
        top.addWidget(label('Software updates', 'sectionTitle'), 1)
        top.addWidget(label('PRIVATE RELEASES', 'privateBadge'))
        update.addLayout(top)
        status_box = QFrame()
        status_box.setObjectName('updateStatusBox')
        status = QHBoxLayout(status_box)
        status.setContentsMargins(18, 18, 18, 18)
        status.setSpacing(15)
        self.mark = StatusMark()
        status.addWidget(self.mark, 0, Qt.AlignmentFlag.AlignTop)
        words = QVBoxLayout()
        words.setSpacing(7)
        self.status_title = label('', 'updateTitle', True)
        self.status_detail = plain_note('')
        words.addWidget(self.status_title)
        words.addWidget(self.status_detail)
        status.addLayout(words, 1)
        update.addWidget(status_box)
        self.last_checked = plain_note('Last checked: Never')
        update.addWidget(self.last_checked)
        actions = QHBoxLayout()
        actions.setSpacing(12)
        self.check_button = button('Check for updates', self.check_for_updates)
        self.check_button.setMinimumWidth(174)
        self.check_button.setMinimumHeight(30)
        self.download_button = button('Download update', self.download_update, primary=True)
        self.download_button.setMinimumWidth(174)
        self.download_button.setMinimumHeight(30)
        actions.addWidget(self.check_button)
        actions.addWidget(self.download_button)
        actions.addStretch(1)
        self.notes_button = QPushButton('Release notes')
        self.notes_button.setObjectName('aboutLink')
        self.notes_button.clicked.connect(self.show_release_notes)
        actions.addWidget(self.notes_button)
        update.addLayout(actions)
        self.progress_row = QWidget()
        progress_layout = QHBoxLayout(self.progress_row)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(22)
        progress_layout.addWidget(self.progress_bar, 1)
        self.cancel_button = button('Cancel', self.cancel_request)
        progress_layout.addWidget(self.cancel_button)
        update.addWidget(self.progress_row)
        self.download_note = plain_note('')
        update.addWidget(self.download_note)
        root.addWidget(self.update_card)
        account = QFrame()
        account.setObjectName('accountRow')
        account_layout = QHBoxLayout(account)
        account_layout.setContentsMargins(0, 0, 0, 0)
        account_words = QVBoxLayout()
        account_words.setSpacing(5)
        account_words.addWidget(label('GitHub access', 'accountTitle'))
        self.account_detail = plain_note('')
        account_words.addWidget(self.account_detail)
        account_layout.addLayout(account_words, 1)
        self.account_button = button('Connect GitHub', self.connect_github)
        account_layout.addWidget(self.account_button, 0, Qt.AlignmentFlag.AlignVCenter)
        self.disconnect_button = button('Disconnect', self.disconnect_github)
        account_layout.addWidget(self.disconnect_button, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addWidget(account)
        root.addStretch(1)

    def retheme(self, *args):
        c = COLORS[theme_manager().mode]
        self.setStyleSheet(f'''
            QFrame#aboutCard {{ background:{c['panel']}; border:1px solid {c['border']}; border-radius:12px; }}
            QFrame#aboutDivider {{ background:{c['border']}; border:0; }}
            QFrame#updateStatusBox {{ background:{c['bg']}; border:1px solid {c['border']}; border-radius:8px; }}
            QLabel#aboutBrand {{ font-size:23pt; font-weight:650; }}
            QLabel#aboutValue {{ font-size:13pt; font-weight:600; }}
            QLabel#updateTitle {{ font-size:16pt; font-weight:600; }}
            QLabel#accountTitle {{ font-size:11pt; font-weight:600; }}
            QLabel#privateBadge {{ color:{c['accent']}; background:{c['hover']}; border-radius:5px; padding:5px 9px; font-size:8pt; font-weight:650; }}
            QPushButton#aboutLink {{ border:0; background:transparent; color:{c['accent']}; padding:7px 0; }}
        ''')
        self.mark.update()

    def _set_state(self, state, detail=None):
        self.state = state
        states = {
            'signin': ('Connect GitHub to check for updates', 'Connect an approved GitHub account to access private releases.'),
            'not_checked': ('Updates have not been checked', 'Check for the latest stable release using your saved GitHub access.'),
            'checking': ('Checking for updates', 'Contacting the private release repository…'),
            'available': ('An update is available', 'A newer compatible release is ready to download.'),
            'current': ('You’re up to date', 'You have the latest compatible stable version of Optical Design Studio.'),
            'no_releases': ('No releases published yet', 'Your connection is working. Check again after a release is published.'),
            'no_compatible': ('No compatible update is available', 'No published package matches this platform. This does not confirm that the application is up to date.'),
            'error': ('Could not check for updates', 'Please try again.'),
            'cancelled': ('Update request cancelled', 'Check again whenever you are ready.'),
            'downloading': ('Downloading update', 'The package will be checked before it is saved.'),
            'downloaded': ('Update downloaded', 'Open the download folder when you are ready to install the update.'),
        }
        title, default_detail = states[state]
        self.status_title.setText(title)
        self.status_detail.setText(detail or default_detail)
        self.mark.kind = state
        self.mark.update()
        can_download = state == 'available' and self._release is not None
        downloaded = state == 'downloaded' and self._downloaded_path is not None
        self.download_button.setVisible(can_download or downloaded)
        self.download_button.setText('Open download folder' if downloaded else 'Download update')
        self.notes_button.setVisible((can_download or downloaded) and self._release is not None)
        self.progress_row.setVisible(state in ('checking', 'downloading'))
        self.check_button.setEnabled(not self.busy)
        self.account_button.setEnabled(not self.busy)
        self.disconnect_button.setEnabled(not self.busy)
        self.cancel_button.setEnabled(True)
        self.download_note.setText('Download the update, then choose when to install it.' if can_download else
            ('The application will not run the installer automatically.' if downloaded else
             'Your projects, materials and saved results remain in your local library.'))

    def _refresh_account(self):
        if not self._token:
            text = 'Not connected · Approved accounts only'
        elif self._username:
            text = f'Connected as {self._username} · Approved accounts only'
        else:
            text = 'Saved GitHub access · Check to verify connection'
        if self._connection_note:
            text += '\n' + self._connection_note
        self.account_detail.setText(text)
        self.account_button.setText('Manage connection' if self._token else 'Connect GitHub')
        self.disconnect_button.setVisible(bool(self._token))

    def connect_github(self):
        if self.busy:
            return
        dialog = ConnectionDialog(self._credentials, self)
        try:
            if dialog.exec() == QDialog.DialogCode.Accepted:
                token, remember = dialog.take_credentials()
                self.begin_connection(token, remember)
        finally:
            dialog.token_edit.clear()
            dialog.deleteLater()

    def begin_connection(self, token, remember=False):
        """Commit a replacement connection only after its access check succeeds."""
        if self.busy or not token or not token.strip():
            return
        self._pending_connection = (token.strip(), bool(remember))
        self._start('check', token.strip(), (self.info['version'], self.info['platform_id']))

    def disconnect_github(self):
        if self.busy:
            return
        self._connection_note = ''
        try:
            self._credentials.delete()
        except Exception:
            self._connection_note = 'Disconnected for this session. Saved access could not be removed; remove it from your OS credential store.'
        self._token = self._username = self._release = self._downloaded_path = None
        self._set_state('signin')
        self._refresh_account()

    def check_for_updates(self):
        if self.busy:
            return
        if not self._token:
            self.connect_github()
            return
        self._start('check', self._token, (self.info['version'], self.info['platform_id']))

    def download_update(self):
        if self.busy:
            return
        if self.state == 'downloaded' and self._downloaded_path is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._downloaded_path.parent)))
            return
        if self.state != 'available' or self._release is None or not self._token:
            return
        directory = QFileDialog.getExistingDirectory(self, 'Save update in folder', str(Path.home() / 'Downloads'))
        if directory:
            self._start('download', self._token, (self._release, Path(directory)))

    def _start(self, operation, token, args):
        if self.busy:
            return
        if operation == 'check':
            self._release = None
        self._downloaded_path = None
        worker = UpdateWorker(self._client_factory, token, operation, args, self)
        self._worker = worker
        worker.progress.connect(self._update_progress)
        worker.finished.connect(self._finish)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFormat('Checking…' if operation == 'check' else 'Downloading…')
        self._set_state('checking' if operation == 'check' else 'downloading')
        worker.start()

    def _update_progress(self, done, total):
        if not self.busy or self._worker.operation != 'download':
            return
        if total and total > 0:
            self.progress_bar.setRange(0, 1000)
            self.progress_bar.setValue(min(1000, int(1000 * done / total)))
            self.progress_bar.setFormat(f'{done / 1048576:.1f} / {total / 1048576:.1f} MB')
        else:
            self.progress_bar.setRange(0, 0)

    def cancel_request(self):
        if self._worker is not None:
            self._worker.cancel()
            self.cancel_button.setEnabled(False)
            self.status_detail.setText('Cancelling the request safely…')

    def _finish(self):
        worker = self._worker
        if worker is None:
            return
        self._worker = None
        pending = self._pending_connection
        self._pending_connection = None
        try:
            if worker.cancelled:
                self._release = None
                self._set_state('cancelled')
            elif worker.error is not None:
                self._release = None
                self._set_state('error', worker.error)
                self.status_title.setText('Could not download update' if worker.operation == 'download'
                    else ('Could not connect GitHub' if pending else 'Could not check for updates'))
            elif worker.operation == 'download':
                self._downloaded_path = Path(worker.result)
                self._set_state('downloaded', f'Verified package saved as {self._downloaded_path.name}.')
            else:
                result = worker.result
                if pending:
                    self._token, remember = pending
                    self._connection_note = 'Access is saved for this session only.'
                    try:
                        if remember:
                            self._credentials.save(self._token)
                            self._connection_note = 'Access remembered in ' + str(self._credentials.storage_label) + '.'
                        else:
                            self._credentials.delete()
                    except Exception:
                        self._connection_note = ('Connected for this session. Credential storage could not be updated; '
                                                 'any previously saved access may remain in the OS credential store.')
                self._username = result.username
                self._release = result.release if result.status == 'available' else None
                self.last_checked.setText('Last checked: ' + display_time(result.checked_at) + ' · Stable channel')
                self._set_state(result.status)
                if result.status == 'available' and self._release is not None:
                    self.status_detail.setText(f'Version {self._release.version} is ready to download for {self.info["platform"]}.')
            self._refresh_account()
        finally:
            worker.deleteLater()
            self.idle.emit()

    def show_release_notes(self):
        if self._release is None:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(f'Release notes · {self._release.version}')
        dialog.resize(630, 460)
        layout = QVBoxLayout(dialog)
        layout.addWidget(plain_note('Published: ' + display_time(self._release.published_at)))
        text = QPlainTextEdit()
        text.setReadOnly(True)
        text.setPlainText(self._release.notes or 'No release notes were provided.')
        layout.addWidget(text, 1)
        layout.addWidget(button('View private repository', lambda: QDesktopServices.openUrl(QUrl(REPOSITORY_URL))))
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(dialog.reject)
        layout.addWidget(close)
        dialog.exec()
        dialog.deleteLater()

    def shutdown(self):
        """Host must defer destruction until idle; socket operations have a timeout."""
        if self.busy:
            self.cancel_request()
            return False
        return True
