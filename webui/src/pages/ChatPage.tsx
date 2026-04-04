import { AppShell } from "../components/layout/AppShell";
import { Sidebar } from "../components/sidebar/Sidebar";
import { ChatView } from "../components/chat/ChatView";
import { useChatApp } from "../hooks/useChatApp";

export function ChatPage() {
  const {
    currentUser,
    chats,
    activeChatId,
    activeMessages,
    loadingMessages,
    sending,
    appError,
    assistantMode,
    settings,
    attachmentRules,
    createChat,
    ensureChatLoaded,
    renameChat,
    archiveChat,
    downloadChat,
    deleteChat,
    setAssistantMode,
    sendMessage,
  } = useChatApp();

  if (!currentUser) {
    return null;
  }

  return (
    <AppShell
      assistantMode={assistantMode}
      availableModes={settings?.available_assistant_modes ?? ["simple", "refine", "thinking"]}
      onAssistantModeChange={setAssistantMode}
      sidebar={
        <Sidebar
          chats={chats}
          gpts={[]}
          activeChatId={activeChatId}
          activeView="chat"
          currentUser={currentUser}
          canUseStandardChat
          canUseGpts
          canUseLibrary
          onCreateGpt={() => undefined}
          onCreateChat={() => void createChat()}
          onOpenLearning={() => undefined}
          onOpenLibrary={() => undefined}
          onOpenAdmin={() => undefined}
          onOpenArchive={() => undefined}
          onOpenInfo={() => undefined}
          onOpenHelp={() => undefined}
          onOpenPreferences={() => undefined}
          onOpenChangePassword={() => undefined}
          onLogout={() => undefined}
          onSelectChat={(chatId) => void ensureChatLoaded(chatId)}
          onSelectGpt={() => undefined}
          onRenameChat={(chatId, chatName) => void renameChat(chatId, chatName)}
          onArchiveChat={(chatId) => void archiveChat(chatId)}
          onOpenChatFilter={() => undefined}
          onDownloadChat={(chatId) => void downloadChat(chatId)}
          onDeleteChat={(chatId) => void deleteChat(chatId)}
          onEditGpt={() => undefined}
          onClearGpt={() => undefined}
          onDownloadGpt={() => undefined}
          onDeleteGpt={() => undefined}
        />
      }
      content={
        <ChatView
          messages={activeMessages}
          sending={sending}
          loadingMessages={loadingMessages}
          error={appError}
          assistantMode={assistantMode}
          attachmentRules={attachmentRules}
          onSend={sendMessage}
        />
      }
    />
  );
}
