import { createContext, PropsWithChildren, useContext, useEffect, useMemo, useState } from "react";

export const languages = [
  { code: "en", name: "English", speech: "en-UG" },
  { code: "lg", name: "Luganda", speech: "lg-UG" },
  { code: "nyn", name: "Runyankole", speech: "nyn-UG" },
  { code: "te", name: "Ateso", speech: "te-UG" },
  { code: "sw", name: "Swahili", speech: "sw-KE" },
] as const;
export type LanguageCode = (typeof languages)[number]["code"];

const messages = {
  en: {
    workspace: "Workspace", dashboard: "Dashboard", administration: "Administration", farms: "Crop management",
    weather: "Weather", advisor: "Planting advisor", disease: "Crop disease check", irrigation: "Smart irrigation",
    yield: "Yield forecast", markets: "Market intelligence", map: "Field monitoring", assistant: "AI assistant",
    questions: "Farmer questions", alerts: "Alerts", analytics: "Reports", fieldTools: "FIELD TOOLS",
    addFarm: "Add a farm", search: "Search farms, crops...", signOut: "Sign out", profile: "Profile settings",
    welcome: "Welcome back", today: "Here’s what’s happening across your farms today.", totalFields: "Total fields",
    totalArea: "Total area", cropTypes: "Crop types", observedDays: "Observed days", voiceInput: "Speak your question",
    listen: "Listen to this answer", stopSpeaking: "Stop speaking", voiceUnsupported: "Voice input is not available in this browser.",
    offline: "Offline · showing saved farm information", online: "Back online · syncing your workspace",
    language: "Preferred language", save: "Save changes", onboarding: "Set up your farm workspace",
    next: "Continue", back: "Back", skip: "Skip this step", finish: "Finish setup",
  },
  lg: {
    workspace: "Ekifo ky’emirimu", dashboard: "Olupapula olukulu", administration: "Obuddukanya", farms: "Okulabirira ebirime",
    weather: "Embeera y’obudde", advisor: "Amagezi g’okusimba", disease: "Okukebera endwadde z’ebirime", irrigation: "Okufukirira",
    yield: "Okuteebereza amakungula", markets: "Emiwendo gy’akatale", map: "Okulondoola ennimiro", assistant: "Omuyambi wa AI",
    questions: "Ebibuuzo by’abalimi", alerts: "Obulabula", analytics: "Lipoota", fieldTools: "EBIKOZESOBWA MU NNIMIRO",
    addFarm: "Yongerako ennimiro", search: "Noonya ennimiro n’ebirime...", signOut: "Fuluma", profile: "Enteekateeka ya akawunti",
    welcome: "Tukwanirizza nate", today: "Laba ebigenda mu maaso mu nnimiro zo leero.", totalFields: "Ennimiro zonna",
    totalArea: "Obunene bw’ennimiro", cropTypes: "Ebika by’ebirime", observedDays: "Ennaku ezikebereddwa", voiceInput: "Yogera ekibuuzo kyo",
    listen: "Wuliriza eky’okuddamu", stopSpeaking: "Komya okwogera", voiceUnsupported: "Okwogera tekukola mu browser eno.",
    offline: "Tewali yintaneeti · olaba ebikwata ku nnimiro ebiterekeddwa", online: "Yintaneeti ezze · nga tutereeza ebikwata ku mirimu",
    language: "Olulimi lw’oyagala", save: "Tereka enkyukakyuka", onboarding: "Tegeka ekifo kyo eky’obulimi",
    next: "Weyongereyo", back: "Ddayo", skip: "Buuka ekitundu kino", finish: "Maliriza enteekateeka",
  },
  nyn: {
    workspace: "Ekiikaro ky’emirimo", dashboard: "Obubasha obukuru", administration: "Okwebembera", farms: "Okureeba eby’obuhingi",
    weather: "Embeera y’obwire", advisor: "Obuhabuzi bw’okubiba", disease: "Kyebera endwara z’ebihingwa", irrigation: "Okuta amaizi",
    yield: "Okuteebereza omwero", markets: "Eby’obushuubuzi", map: "Ekiishushani ky’ebyaro", assistant: "Omuhwezi wa AI",
    questions: "Ebibuuzo by’abahingi", alerts: "Okurabura", analytics: "Ebirikureebwa", fieldTools: "EBIKOZESIBWA OMU BYARO",
    addFarm: "Yongeraho ekyaro", search: "Ronda ebyaro n’eby’okubiba...", signOut: "Rugaamu", profile: "Entebeekanisa y’ekikonti",
    welcome: "Tukwanirize kandi", today: "Eki nikyo kiri kubaho omu byaro byawe erizooba.", totalFields: "Ebyaro byona",
    totalArea: "Obugazi bw’ebyaro", cropTypes: "Eby’okubiba ebya buriinye", observedDays: "Eizooba ezirikurebwa", voiceInput: "Gamba ekibuuzo kyawe",
    listen: "Hurira eky’okugarukamu", stopSpeaking: "Rekera aho kugamba", voiceUnsupported: "Okugamba tikurikukora omu browser egi.",
    offline: "Tihariho yintaneeti · nooreeba ebikwatiraine n’ekyaro ebibikirwe", online: "Yintaneeti egarukire · nitutereeza ebikwatiraine n’emirimo",
    language: "Orurimi orw’oyenda", save: "Bika empinduka", onboarding: "Teekateeka ekifo kyawe ky’obuhingi",
    next: "Gumizamu", back: "Garuka enyuma", skip: "Renga ekicweka eki", finish: "Mara enteekateeka",
  },
  sw: {
    workspace: "Eneo la kazi", dashboard: "Dashibodi", administration: "Usimamizi", farms: "Usimamizi wa mashamba",
    weather: "Hali ya hewa", advisor: "Mshauri wa upandaji", disease: "Ukaguzi wa magonjwa ya mimea", irrigation: "Umwagiliaji mahiri",
    yield: "Makadirio ya mavuno", markets: "Taarifa za masoko", map: "Ufuatiliaji wa mashamba", assistant: "Msaidizi wa AI",
    questions: "Maswali ya wakulima", alerts: "Tahadhari", analytics: "Ripoti", fieldTools: "ZANA ZA SHAMBA",
    addFarm: "Ongeza shamba", search: "Tafuta mashamba, mazao...", signOut: "Ondoka", profile: "Mipangilio ya wasifu",
    welcome: "Karibu tena", today: "Haya ndiyo yanayoendelea kwenye mashamba yako leo.", totalFields: "Mashamba yote",
    totalArea: "Eneo lote", cropTypes: "Aina za mazao", observedDays: "Siku zilizorekodiwa", voiceInput: "Uliza swali kwa sauti",
    listen: "Sikiliza jibu", stopSpeaking: "Sitisha sauti", voiceUnsupported: "Uingizaji wa sauti haupatikani kwenye kivinjari hiki.",
    offline: "Nje ya mtandao · taarifa zilizohifadhiwa zinaonyeshwa", online: "Mtandao umerejea · tunasawazisha taarifa",
    language: "Lugha unayopendelea", save: "Hifadhi mabadiliko", onboarding: "Sanidi akaunti yako ya shamba",
    next: "Endelea", back: "Rudi", skip: "Ruka hatua hii", finish: "Maliza usanidi",
  },
} satisfies Record<Exclude<LanguageCode, "te">, Record<string, string>>;

type MessageKey = keyof typeof messages.en;
const LanguageContext = createContext<{ language: LanguageCode; setLanguage: (language: LanguageCode) => void; t: (key: MessageKey) => string } | null>(null);

export function LanguageProvider({ children }: PropsWithChildren) {
  const [language, setLanguageState] = useState<LanguageCode>(() => {
    const saved = localStorage.getItem("agri_language");
    return languages.some((item) => item.code === saved) ? saved as LanguageCode : "en";
  });
  const setLanguage = (next: LanguageCode) => { setLanguageState(next); localStorage.setItem("agri_language", next); };
  useEffect(() => { document.documentElement.lang = languages.find((item) => item.code === language)?.speech ?? "en"; }, [language]);
  const value = useMemo(() => ({ language, setLanguage, t: (key: MessageKey) => (language === "te" ? messages.en[key] : messages[language][key]) ?? messages.en[key] }), [language]);
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) throw new Error("useLanguage must be used within LanguageProvider");
  return context;
}
