"""Gera o arquivo PDF de documentação completa e plano de implementação do H.E.R.O. em 2 páginas bem diagramadas."""
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak
)

def build_pdf(filename="docs/DOCUMENTACAO_E_PLANO_HERO.pdf"):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    accent_blue = colors.HexColor("#0284c7")
    primary_dark = colors.HexColor("#0f172a")
    text_dark = colors.HexColor("#334155")
    bg_table_head = colors.HexColor("#0369a1")
    bg_table_alt = colors.HexColor("#f8fafc")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=accent_blue,
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=10
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=primary_dark,
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#0369a1"),
        spaceBefore=8,
        spaceAfter=3,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=text_dark,
        spaceAfter=5
    )

    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=text_dark
    )
    cell_head = ParagraphStyle(
        'TableHead',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white
    )

    elements = []

    # ==================== PÁGINA 1 ====================
    elements.append(Paragraph("Assistente Pessoal H.E.R.O. (J.A.R.V.I.S. Core)", title_style))
    elements.append(Paragraph("Documentação Técnica & Arquitetural do Sistema Multi-Agente Stark<br/><b>Autor:</b> Douglas &bull; <b>Arquitetura:</b> 100% Local, Privada e Reativa", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=accent_blue, spaceAfter=8))

    elements.append(Paragraph("1. Visão Geral do Ecossistema", h1_style))
    elements.append(Paragraph(
        "O <b>Assistente Pessoal H.E.R.O.</b> é uma plataforma de inteligência artificial de voz e raciocínio multi-agente "
        "projetada para rodar com privacidade absoluta no hardware local (sem depender de APIs externas pagas). "
        "Integrado ao Docker e Ollama, oferece comunicação bidirecional com baixa latência, reator Arc com Web Audio API, "
        "memória semântica de longo prazo (PostgreSQL + pgvector) e troca automática de agentes baseada no contexto da conversa.",
        body_style
    ))

    elements.append(Paragraph("2. Protocolos de IA Especializados (VisionQuest)", h1_style))
    table_data = [
        [Paragraph("Protocolo", cell_head), Paragraph("Função Primária", cell_head), Paragraph("Especialidades Técnicas", cell_head), Paragraph("Voz Neural (PT-BR)", cell_head)],
        [Paragraph("<b>J.A.R.V.I.S.</b>", cell_style), Paragraph("Núcleo Central & Segurança", cell_style), Paragraph("Coordenação dos protocolos, integridade de dados e proteção central.", cell_style), Paragraph("pt-BR-Antonio", cell_style)],
        [Paragraph("<b>E.D.I.T.H.</b>", cell_style), Paragraph("Cibersegurança Virtual", cell_style), Paragraph("Defesa virtual (Blue Team), auditoria de código, proteção contra SQLi/XSS/DDoS e pentests éticos (Red Team) em sites e apps.", cell_style), Paragraph("pt-BR-Thalita", cell_style)],
        [Paragraph("<b>F.R.I.D.A.Y.</b>", cell_style), Paragraph("Socialização & Empatia", cell_style), Paragraph("Inteligência relacional, condução de conversas difíceis, psicologia, aconselhamento empático e humor.", cell_style), Paragraph("pt-BR-Francisca", cell_style)],
        [Paragraph("<b>D.U.M.-E & U</b>", cell_style), Paragraph("Manutenção & Mídia", cell_style), Paragraph("<b>U:</b> análise técnica de mídia, vídeos e arquivos.<br/><b>DUM-E:</b> faxina de cache, expurgo de logs e estabilidade.", cell_style), Paragraph("pt-BR-Antonio", cell_style)]
    ]
    t = Table(table_data, colWidths=[75, 120, 245, 100])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), bg_table_head),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, bg_table_alt]),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 6))

    elements.append(Paragraph("3. Pilares Técnicos de Engenharia", h1_style))
    elements.append(Paragraph(
        "&bull; <b>Roteamento Semântico Inteligente:</b> Não é obrigatório chamar o agente pelo nome. Ao perguntar sobre invasão, brechas ou segurança web, <b>E.D.I.T.H.</b> assume automaticamente com o HUD violeta. Temas relacionais ativam <b>F.R.I.D.A.Y.</b> e limpeza de sistema ativa <b>D.U.M.-E</b>.<br/>"
        "&bull; <b>Memória Semântica Vetorial (Hipocampo):</b> PostgreSQL 16 com extensão <i>pgvector</i> e embeddings locais <i>nomic-embed-text</i> (768 dimensões). Aprendizado de fatos em tempo real com prevenção de duplicação semântica.<br/>"
        "&bull; <b>Pipeline de Áudio de Baixa Latência:</b> Reconhecimento de fala via <i>faster-whisper</i> local (com VAD e pré-aquecimento assíncrono) e síntese <i>edge-tts</i> fragmentada por sentenças via WebSocket com suporte a <i>Barge-in</i> (interrupção imediata por fala ou tecla Esc).<br/>"
        "&bull; <b>HUD Futurista Reator Arc:</b> Desenvolvido em HTML5 Canvas, Web Audio API e glassmorphism reativo às frequências vocais.",
        body_style
    ))

    elements.append(PageBreak())

    # ==================== PÁGINA 2 ====================
    elements.append(Paragraph("Plano de Implementação Passo a Passo (Deploy Local)", title_style))
    elements.append(Paragraph("Roteiro completo para replicação do Assistente H.E.R.O. em novos computadores ou servidores", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=accent_blue, spaceAfter=8))

    elements.append(Paragraph("Fase 1: Preparação do Ambiente Host", h1_style))
    elements.append(Paragraph(
        "<b>1. Docker Desktop:</b> Instale o Docker e confirme que o motor WSL2 está ativado.<br/>"
        "<b>2. Ollama:</b> Instale em <font color='#0284c7'>ollama.com</font>. Adicione a variável de ambiente do sistema <code>OLLAMA_HOST=0.0.0.0</code> e reinicie o Ollama para liberar o tráfego dos containers Docker.<br/>"
        "<b>3. Download dos Modelos:</b> Execute no terminal:<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<code>ollama pull qwen2.5:7b</code> (ou <code>qwen2.5:3b</code> para máquinas mais modestas)<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<code>ollama pull nomic-embed-text</code>",
        body_style
    ))

    elements.append(Paragraph("Fase 2: Instalação e Configuração do Projeto", h1_style))
    elements.append(Paragraph(
        "<b>1. Clonagem do Repositório:</b><br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<code>git clone https://github.com/douglas-bsj/assistente-pessoal-hero.git</code><br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<code>cd assistente-pessoal-hero</code><br/>"
        "<b>2. Configuração do Arquivo de Ambiente:</b><br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;Copie <code>.env.example</code> para <code>.env</code> e personalize seu nome em <code>JARVIS_USER_NAME=SeuNome</code>.",
        body_style
    ))

    elements.append(Paragraph("Fase 3: Inicialização dos Containers", h1_style))
    elements.append(Paragraph(
        "Execute no terminal raiz do projeto:<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<code>docker compose up --build -d</code><br/>"
        "Aguarde o download e inicialização dos serviços <code>jarvis-db</code> e <code>jarvis-core</code>. Para acompanhar os logs de inicialização:<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<code>docker compose logs -f jarvis-core</code>",
        body_style
    ))

    elements.append(Paragraph("Fase 4: Operação no HUD e Recursos", h1_style))
    elements.append(Paragraph(
        "<b>1. Acesso Web:</b> Acesse <b>http://localhost:8000</b> no navegador e permita o microfone.<br/>"
        "<b>2. Controles de Áudio e Atalhos:</b><br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&bull; <b>Barra de Espaço:</b> Pressione e segure para falar (Push-to-Talk).<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&bull; <b>Esc:</b> Corta a fala do assistente instantaneamente (Barge-In).<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&bull; <b>Mãos-Livres:</b> Habilite o modo contínuo de ativação por voz (VAD).<br/>"
        "<b>3. Gerenciamento de Memória (Hipocampo):</b> Clique no botão <b>Hipocampo</b> para auditar, buscar ou apagar memórias salvas.",
        body_style
    ))

    elements.append(Paragraph("Fase 5: Manutenção e Resolução de Problemas", h1_style))
    elements.append(Paragraph(
        "&bull; <b>Redefinir banco de memórias do zero:</b> <code>docker compose down -v && docker compose up -d</code><br/>"
        "&bull; <b>Economia de memória RAM:</b> Mude <code>OLLAMA_CHAT_MODEL=qwen2.5:3b</code> e <code>WHISPER_MODEL=tiny</code> no <code>.env</code>.<br/>"
        "&bull; <b>Headset P3 no Windows:</b> Selecione <i>Headset com microfone</i> no gerenciador de áudio para evitar captura acidental pelo microfone embutido.",
        body_style
    ))

    elements.append(Spacer(1, 14))
    elements.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#cbd5e1"), spaceAfter=6))
    elements.append(Paragraph("<font color='#64748b' size='8'>Assistente Pessoal H.E.R.O. &bull; Repositório: github.com/douglas-bsj/assistente-pessoal-hero &bull; Desenvolvido por Douglas</font>", ParagraphStyle('Footer', alignment=1)))

    doc.build(elements)
    print("PDF de 2 páginas gerado com sucesso!")

if __name__ == "__main__":
    build_pdf()
