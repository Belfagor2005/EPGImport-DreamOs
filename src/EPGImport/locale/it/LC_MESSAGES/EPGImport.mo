��    p      �  �         p	  H   q	     �	     �	     �	     �	  8   �	     +
     B
     W
     l
     s
     �
     �
     �
  p   �
     6  "   <     _         �  
   �     �  �   �  7   2  i   j  J   �          8     G     Z     y  	   �  ?   �  Q   �  "   .     Q     _  '   y     �     �  (   �     �  &        (     /     ?     W     e     �     �      �  "   �  #   �     "     )  *   0     [  �   r                 #   /     S     n     �     �     �     �     �     �  "   �          *     3  
   N     Y     a  U   }  .   �  .        1     D  .   b     �     �  P   �  �     �   �  N   �     &  i   /     �     �  	   �  [   �  {        �  |   �  K   %     q  @   �  �   �  J   V  :   �     �     �     �     �          $     4  �  G  e        |     �     �     �  :   �            !     =     X     `  (   q     �     �     �     :  6   C  4   z     �  %  �     �      �   �   !  =   �!  �   �!  K   |"     �"     �"     �"  "   #  !   6#  	   X#  ,   b#  [   �#  &   �#     $  $   %$  +   J$     v$     �$  /   �$     �$  ,   �$     %     %     '%     B%     X%     q%  !   �%  "   �%  %   �%  )   �%     %&     -&  :   5&     p&  �   �&     7'     G'  !   P'  (   r'  $   �'     �'     �'     �'     �'  "   �'     (     +(  *   I(     t(     �(  '   �(     �(     �(  "   �(  a   )  D   f)  8   �)     �)     �)  @   *  "   W*     z*  Y   �*  �   �*  �   �+  K   �,     -  d   -     ~-     �-  
   �-  l   �-  �   .     �.  �   �.  R   ;/  "   �/  J   �/  �   �/  ]   �0  8   1     =1     D1     H1     ^1     q1     �1     �1         #   c       3   0   !              J   Q   P             >   :          &       l              V   k      "       i       m                      a          G                  e   p   H   j   9   W   A   F      o   f       6       B   O         [   .          T   ^   /   $          +       (   2      Z          @      R   ?   N         8      M   5   *       n   4   <   C   S       L   )       D   
   `         ;   h   d       X      I       %   1      	                 E   K   U   g   ]   Y   \   _   b   -                       '          =      7   ,    
Import of epg data will start.
This may take a few minutes.
Is this ok?  events
 Add Channel Add Provider All services provider Also apply "channel id" filtering on custom.channels.xml Automated EPG Importer Automatic import EPG Automatic start time Cancel Channel Selection Choice days for start import Choose Directory: Choose directory Choose the action to perform when the box is in deep standby and the automatic EPG update should normally start. Clear Clearing current EPG before import Consider setting "Days Profile" Days Profile Define the number of days that you want to get the full EPG data, reducing this number can help you to save memory usage on your box. But you are also limited with the EPG provider available data. You will not have 15 days EPG if it only provide 7 days data. Delete all Delete selected Display a shortcut "EPG import now" in the extension menu. This menu entry will immediately start the EPG update process when selected. Display a shortcut "EPG import" in the plugins browser. Display a shortcut "EPG import" in your STB epg menu screen. This allows you to access the configuration. Do you want to update Source now?

Wait for the import successful message! EPG Import Configuration EPG Import Log EPG Import Sources EPG Import finished, %d events EPG database was emptied EPGImport EPGImport
Import of epg data is still in progress. Please wait. EPGImport
Import of epg data will start.
This may take a few minutes.
Is this ok? EPGImport Plugin
Failed to start:
 EPGImport now Enter shell command name. Execute shell command before import EPG Filtering: %s Please wait! Friday Hours after which the import is repeated Ignore services list Ignore services list(press OK to save) Import Import from Git Importing: %s %s events Last import:  Last import: %s %s, %d events Last import: %s events Load EPG only for IPTV channels Load EPG only for IPTV channels. Load EPG only services in bouquets Load long descriptions up to X days Manual Monday No active EPG sources found, nothing to do No source file found ! Number of hours (1-23, or 0 for no repeat) after which the import is repeated. This value is not saved and will be reset when the GUI restarts. Path DB EPG Press OK Really delete all list? Return to deep standby after import Run AutoTimer after import SELECT YOUR CHOICE Saturday Save Select action Settings saved successfully ! Shell command name Show "EPGImport" in plugins Show "EPGimport now" in extensions Show "EPGimport" in epg menu Show log Skip import on restart GUI Source EPG Sources Sources saved successfully! Specify in which case the EPG must be automatically updated after the box has booted. Specify the path folder for save EPG.dat file. Specify the time for the automatic EPG update. Standby at startup Start import after booting up Start import after resuming from standby mode. Start import after standby Sunday The waked up box will be turned into standby after automatic EPG import wake up. This is for advanced users that are using the channel id filtering feature. If enabled, the filter rules defined into /etc/epgimport/channel_id_filter.conf will also be applied on your /etc/epgimport/custom.channels.xml file. This will clear the current EPG data in memory before updating the EPG data. This allows you to always have a clean new EPG with the latest EPG data, for example in case of program changes between refresh, otherwise EPG data are cumulative. This will turn back waked up box into deep-standby after automatic EPG import. Thursday To save memory you can decide to only load EPG data for the services that you have in your bouquet files. Tuesday Update Aborted! Wednesday When enabled, it allows you to schedule an automatic EPG update at the given days and time. When enabled, then you can run the desired script before starting the import, after which the import of the EPG will begin. When in deep standby When you decide to import the EPG after the box booted mention if the "days profile" must be take into consideration or not. When you restart the GUI you can decide to skip or not the EPG data import. Write to /tmp/epgimport.log You can select the day(s) when the EPG update must be performed. You can start automatically the plugin AutoTimer after the EPG data update to have it refreshing its scheduling after EPG data refresh. You may not use this settings!
At least one day a week should be included! You must restart Enigma2 to load the EPG data,
is this OK? always never only automatic boot only manual boot press OK to save list skip the import wake up and import Project-Id-Version: EPGImport Italian Translation for Enigma2
Report-Msgid-Bugs-To: 
PO-Revision-Date: 2025-03-17 15:46+0100
Last-Translator: Massimo Pissarello <mapi68@gmail.com>
Language-Team: Italian <>
Language: it_IT
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 8bit
Plural-Forms: nplurals=2; plural=(n != 1);
X-Generator: Poedit 3.5
X-Poedit-Basepath: ../../..
X-Poedit-SourceCharset: UTF-8
X-Poedit-SearchPath-0: .
 
Verrà avviata l'importazione dei dati EPG.
L'operazione potrebbe richiedere alcuni minuti.
Procedo?  eventi
 Aggiungi canale Aggiungi fornitore Fornitore di tutti i servizi Applica anche il filtro "ID canale" su custom.channels.xml Importatore automatizzato di EPG Importazione automatica EPG Orario di avvio automatico Annulla Selezione canale Seleziona i giorni di avvio importazione Scegi cartella: Scegli cartella Scegli l'azione da eseguire quando il ricevitore è spento e l'aggiornamento automatico dell'EPG dovrebbe normalmente iniziare. Cancella Cancellazione dell'EPG attuale prima dell'importazione Valuta la possibilità di impostare "Profilo giorni" Profilo giorni Definisci il numero di giorni di cui desideri ottenere i dati EPG completi. Ridurre questo numero può aiutarti a risparmiare utilizzo della memoria sul ricevitore. Ma sei anche limitato con i dati disponibili del fornitore EPG. Non avrai un EPG di 15 giorni se fornisce solo dati di 7 giorni. Elimina tutto Elimina selezionato Visualizza una scorciatoia "Importa EPG ora" nel menu delle estensioni. Questa voce di menu avvierà immediatamente il processo di aggiornamento EPG quando selezionata. Mostra scorciatoia "Importazione EPG" nel browser dei plugin. Visualizza una scorciatoia "Importazione EPG" nella schermata del menu epg del ricevitore. Questo ti consente di accedere alla configurazione. Vuoi aggiornare Source ora?

Attendi il messaggio di importazione riuscita! Configurazione di EPG Import Registro di EPG Import Sorgenti di EPG Import EPG Import ha terminato, %d eventi Il database EPG è stato svuotato EPGImport EPG Import
Importazione dati EPG in corso... EPG Import
L'importazione dei dati EPG sta per iniziare.
Ci vorrà qualche minuto.
Procedo? Plugin EPG Import
Avvio non riuscito:
 Importa EPG adesso Inserisci il nome del comando shell. Esegui comando shell prima di importare EPG Filtraggio: %s Attendi prego! Venerdì Ore dopo le quali l'importazione viene ripetuta Ignora elenco servizi Ignora elenco servizi (premi OK per salvare) Importa Importa da Git Importazione: %s %s eventi Ultima importazione:  Ultima: %s %s, %d eventi Ultima importazione: %s eventi Carica EPG solo per i canali IPTV Carica EPG solo per i canali IPTV. Carica solo i servizi EPG nei bouquet Carica descrizioni lunghe fino a X giorni Manuale Lunedì Nessuna sorgente EPG attiva trovata, non posso fare niente Nessun file sorgente trovato! Numero di ore (1-23 o 0 per nessuna ripetizione) dopo le quali viene ripetuta l'importazione. Questo valore non viene salvato e verrà reimpostato al riavvio della GUI. Cartella DB EPG Premi OK Eliminare davvero tutta la lista? Spegni completamente dopo l'importazione Esegui AutoTimer dopo l'importazione SELEZIONA E SCEGLI Sabato Salva Seleziona azione Impostazioni salvate con successo! Nome del comando shell Mostra "EPGImport" in plugins Mostra "EPGImport adesso" nelle estensioni Mostra "EPGImport" in menu epg Mostra registro Salta importazione al riavvio della GUI Sorgenti EPG Sorgenti Impostazioni salvate con successo! Specifica in quale caso l'EPG deve essere aggiornato automaticamente dopo l'avvio del ricevitore. Specificare la cartella del percorso in cui salvare il file EPG.dat. Specificare l'orario per l'aggiornamento automatico EPG. Standby all'avvio Avvia importazione dopo il boot Avvia l'importazione dopo essere uscito dalla modalità standby. Avvia importazione dopo lo standby Domenica Il ricevitore verrà messo in standby dopo l'accensione automatica dell'importazione EPG. Per gli utenti avanzati che utilizzano la funzione di filtraggio dell'ID canale. Se abilitate, le regole di filtro definite in /etc/epgimport/channel_id_filter.conf verranno applicate anche al file /etc/epgimport/custom.channels.xml. Cancella i dati EPG in memoria prima di aggiornare i dati EPG. Consente di avere sempre un nuovo EPG pulito con i dati EPG più recenti, ad esempio in caso di modifiche al programma tra un aggiornamento e l'altro, altrimenti i dati EPG sono cumulativi. Accende il ricevitore, importa automaticamente l'EPG, spegne il ricevitore. Giovedì Per risparmiare memoria puoi decidere di caricare solo i dati EPG per i servizi che hai nei bouquet. Martedì Aggiornamento annullato! Mercoledì Se abilitato, consente di pianificare un aggiornamento automatico dell'EPG nei giorni e all'ora specificati. Se abilitato, è possibile eseguire lo script desiderato prima di avviare l'importazione, dopodiché inizierà l'importazione dell'EPG. Quando è spento Quando decidi di importare l'EPG dopo l'avvio del ricevitore indica se il "Profilo giorni" deve essere preso in considerazione oppure no. Quando riavvii la GUI puoi decidere di saltare o meno l'importazione dei dati EPG. Scrivi in ​​/tmp/epgimport.log Puoi selezionare i giorni in cui deve essere eseguito l'aggiornamento EPG. Puoi avviare automaticamente il plugin AutoTimer dopo l'aggiornamento dei dati EPG per fare in modo che aggiorni la sua pianificazione dopo l'aggiornamento dei dati EPG. Non puoi usare queste impostazioni!
Dovrebbe essere incluso almeno un giorno della settimana! Devi riavviare Enigma2 per caricare i dati EPG,
procedo? sempre mai solo avvio automatico solo avvio manuale premere OK per salvare l'elenco salta importazione accendi e importa 