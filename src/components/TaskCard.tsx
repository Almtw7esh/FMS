import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Send } from "lucide-react";
import { FaWhatsapp } from "react-icons/fa";

// WhatsApp group info type
type WhatsAppGroup = {
  name: string;
  link: string;
};

interface TaskCardProps {
  id: string;
  caseNumber: string;
  fbgNumber: string;
  title: string;
  createdBy: string;
  assignedTo: string;
  category: string;
  status: string;
  commentCount: number;
  attachmentCount: number;
  whatsappGroups?: WhatsAppGroup[];
  lastMessage?: string;
  lastMessageDate?: string;
  uuid?: string;
}

import { useNavigate } from 'react-router-dom';

const TaskCard = ({
  id,
  caseNumber,
  fbgNumber,
  title,
  createdBy,
  assignedTo,
  category,
  status,
  commentCount,
  attachmentCount,
  whatsappGroups,
  lastMessage,
  lastMessageDate,
  uuid,
}: TaskCardProps) => {
  const navigate = useNavigate();
  const formatCardInfo = () => {
    return `*Task Details*\n\nID: ${id}\nCase: ${caseNumber}\nFBG: ${fbgNumber}\nTitle: ${title}\nCreated By: ${createdBy}\nAssigned To: ${assignedTo}\nCategory: ${category}\nStatus: ${status}\nComments: ${commentCount}\nAttachments: ${attachmentCount}`;
  };

  // Send to specific WhatsApp group
  const handleWhatsAppShare = (groupLink: string) => {
    const message = encodeURIComponent(formatCardInfo());
    window.open(`${groupLink}?text=${message}`, '_blank');
  };

  const handleTelegramShare = () => {
    const message = encodeURIComponent(formatCardInfo());
    window.open(`https://t.me/share/url?url=&text=${message}`, '_blank');
  };

  return (
    <Card className="bg-fms-card border-fms-border hover:bg-fms-card-hover transition-colors p-6 mb-4 min-h-[180px]">
      <div className="space-y-4">
        {/* Header: Case Number (bold) and FBG (zone) */}
        <div className="flex items-center justify-between">
          <span className="text-base font-bold text-blue-400">{caseNumber}</span>
          <span className="text-xs font-semibold text-green-400 ml-2">{fbgNumber}</span>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>{commentCount} ??</span>
            <span>?{attachmentCount}</span>
            <span>??</span>
            {/* Message icon and last message */}
            {uuid && (
              <span
                className="cursor-pointer flex items-center gap-1"
                title="View messages"
                onClick={() => window.open(`https://msp.go2field.iq/task/${uuid}`, '_blank')}
              >
                <span role="img" aria-label="messages">???</span>
                {lastMessageDate && (
                  <span className="ml-1">
                    {lastMessageDate}
                  </span>
                )}
              </span>
            )}
          </div>
        </div>

        {/* Card Title and Info */}
        <div className="space-y-1">
          <p className="text-sm text-white font-medium">{title}</p>
          <p className="text-xs text-muted-foreground">{createdBy}</p>
          <p className="text-xs text-muted-foreground">{assignedTo}</p>
        </div>

        {/* Social Icons */}
        <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-fms-border overflow-hidden">
          {/* WhatsApp Groups (custom demo) */}
          <button
            onClick={() => handleWhatsAppShare("https://chat.whatsapp.com/Dd6Zim7zP0b906Mmc683tx")}
            className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg bg-fms-whatsapp/10 hover:bg-fms-whatsapp/20 transition-colors cursor-pointer"
            title="Send to ???? ????? fms"
          >
            <FaWhatsapp className="w-4 h-4 text-fms-whatsapp" />
            <span className="text-xs font-medium text-fms-whatsapp">???? ????? fms</span>
          </button>
          <button
            onClick={() => handleWhatsAppShare("https://chat.whatsapp.com/JbDxFoRHiWC00UOEY4MTWh")}
            className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg bg-fms-whatsapp/10 hover:bg-fms-whatsapp/20 transition-colors cursor-pointer"
            title="Send to ???? FMS"
          >
            <FaWhatsapp className="w-4 h-4 text-fms-whatsapp" />
            <span className="text-xs font-medium text-fms-whatsapp">???? FMS</span>
          </button>
          <button
            onClick={() => handleWhatsAppShare("https://chat.whatsapp.com/IqmsU029e9d302Vppa3VoA")}
            className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg bg-fms-whatsapp/10 hover:bg-fms-whatsapp/20 transition-colors cursor-pointer"
            title="Send to ???? FMS"
          >
            <FaWhatsapp className="w-4 h-4 text-fms-whatsapp" />
            <span className="text-xs font-medium text-fms-whatsapp"> ???????? ????? FMS</span>
          </button>
          <button
            onClick={() => handleWhatsAppShare("https://chat.whatsapp.com/GdUt54IuG7hCzQE6kLiSfj")}
            className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg bg-fms-whatsapp/10 hover:bg-fms-whatsapp/20 transition-colors cursor-pointer"
            title="Send to ???? FMS"
          >
            <FaWhatsapp className="w-4 h-4 text-fms-whatsapp" />
            <span className="text-xs font-medium text-fms-whatsapp"> ???? ????? FMS</span>
          </button>
          <button
            onClick={() => handleWhatsAppShare("https://chat.whatsapp.com/IqmsU029e9d302Vppa3VoA")}
            className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg bg-fms-whatsapp/10 hover:bg-fms-whatsapp/20 transition-colors cursor-pointer"
            title="Send to ???? FMS"
          >
            <FaWhatsapp className="w-4 h-4 text-fms-whatsapp" />
            <span className="text-xs font-medium text-fms-whatsapp"> ????? ????? FMS</span>
          </button>

          
          {/* Telegram */}
          <button
            onClick={handleTelegramShare}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-fms-telegram/10 hover:bg-fms-telegram/20 transition-colors cursor-pointer"
            title="Share to Telegram"
          >
            <Send className="w-4 h-4 text-fms-telegram" />
            <span className="text-xs font-medium text-fms-telegram">fms.earth</span>
          </button>
        </div>

        {/* Tags */}
        <div className="flex flex-wrap gap-2 pt-2">
          <Badge variant="secondary" className="text-xs bg-fms-tag-green/10 text-fms-tag-green border-0">
            {category}
          </Badge>
          <Badge variant="secondary" className="text-xs bg-fms-tag-blue/10 text-fms-tag-blue border-0">
            {status}
          </Badge>
        </div>
      </div>
    </Card>
  );
};

export default TaskCard;
