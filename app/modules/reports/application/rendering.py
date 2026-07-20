"""Builds the (title, headers, rows) table for each report type from real
attendance data — no fabricated numbers, every column traces back to a field
already stored on `AttendanceEntity`."""

from collections import defaultdict

from app.modules.attendances.domain.entities import AttendanceEntity
from app.modules.reports.domain.entities import ReportType


def build_report_rows(report_type: ReportType, attendances: list[AttendanceEntity]) -> tuple[str, list[str], list[list[str]]]:
    if report_type == ReportType.PRODUTIVIDADE:
        return _productivity(attendances)
    if report_type == ReportType.ESTATISTICO:
        return _statistics(attendances)
    if report_type == ReportType.TEMPO_EFICIENCIA:
        return _efficiency(attendances)
    if report_type == ReportType.GEOGRAFICO:
        return _geographic(attendances)
    if report_type == ReportType.FOTOS:
        return _photos(attendances)
    if report_type == ReportType.EXECUTIVO:
        return _executive(attendances)
    return _attendances(attendances)


def _attendances(attendances: list[AttendanceEntity]) -> tuple[str, list[str], list[list[str]]]:
    headers = ["Data", "Operador", "Formulário", "Duração (s)", "Fotos", "Assinatura", "GPS"]
    rows = [
        [
            attendance.created_at.isoformat(),
            attendance.operator_name,
            attendance.form_name,
            str(attendance.duration),
            str(len(attendance.photos)),
            "Sim" if attendance.signature else "Não",
            f"{attendance.gps_location.latitude:.5f}, {attendance.gps_location.longitude:.5f}" if attendance.gps_location else "—",
        ]
        for attendance in attendances
    ]
    return "Atendimentos", headers, rows


def _productivity(attendances: list[AttendanceEntity]) -> tuple[str, list[str], list[list[str]]]:
    by_operator: dict[str, list[AttendanceEntity]] = defaultdict(list)
    for attendance in attendances:
        by_operator[attendance.operator_name].append(attendance)

    headers = ["Operador", "Atendimentos", "Duração Média (s)"]
    rows = sorted(
        (
            [operator_name, str(len(items)), str(int(sum(a.duration for a in items) / len(items)))]
            for operator_name, items in by_operator.items()
        ),
        key=lambda row: int(row[1]),
        reverse=True,
    )
    return "Produtividade por Operador", headers, rows


def _statistics(attendances: list[AttendanceEntity]) -> tuple[str, list[str], list[list[str]]]:
    total = len(attendances)
    avg_duration = int(sum(a.duration for a in attendances) / total) if total else 0
    unique_operators = len({a.operator_id for a in attendances})
    unique_forms = len({a.form_id for a in attendances})
    with_gps = sum(1 for a in attendances if a.gps_location is not None)
    with_signature = sum(1 for a in attendances if a.signature)
    with_photos = sum(1 for a in attendances if a.photos)

    headers = ["Métrica", "Valor"]
    rows = [
        ["Total de atendimentos", str(total)],
        ["Operadores únicos", str(unique_operators)],
        ["Formulários únicos", str(unique_forms)],
        ["Duração média (s)", str(avg_duration)],
        ["Com localização GPS", str(with_gps)],
        ["Com assinatura", str(with_signature)],
        ["Com foto", str(with_photos)],
    ]
    return "Estatísticas Gerais", headers, rows


def _efficiency(attendances: list[AttendanceEntity]) -> tuple[str, list[str], list[list[str]]]:
    headers = ["Operador", "Formulário", "Data", "Duração (s)"]
    ordered = sorted(attendances, key=lambda a: a.duration, reverse=True)
    rows = [
        [attendance.operator_name, attendance.form_name, attendance.created_at.isoformat(), str(attendance.duration)]
        for attendance in ordered
    ]
    return "Tempo e Eficiência", headers, rows


def _geographic(attendances: list[AttendanceEntity]) -> tuple[str, list[str], list[list[str]]]:
    headers = ["Operador", "Formulário", "Data", "Latitude", "Longitude", "Precisão (m)"]
    rows = [
        [
            attendance.operator_name,
            attendance.form_name,
            attendance.created_at.isoformat(),
            f"{attendance.gps_location.latitude:.6f}",
            f"{attendance.gps_location.longitude:.6f}",
            f"{attendance.gps_location.accuracy:.1f}",
        ]
        for attendance in attendances
        if attendance.gps_location is not None
    ]
    return "Localização Geográfica", headers, rows


def _photos(attendances: list[AttendanceEntity]) -> tuple[str, list[str], list[list[str]]]:
    headers = ["Operador", "Formulário", "Data", "Quantidade de Fotos", "Legendas"]
    rows = [
        [
            attendance.operator_name,
            attendance.form_name,
            attendance.created_at.isoformat(),
            str(len(attendance.photos)),
            "; ".join(photo.caption for photo in attendance.photos if photo.caption) or "—",
        ]
        for attendance in attendances
        if attendance.photos
    ]
    return "Fotos Registradas", headers, rows


def _executive(attendances: list[AttendanceEntity]) -> tuple[str, list[str], list[list[str]]]:
    _, _, stat_rows = _statistics(attendances)
    _, _, productivity_rows = _productivity(attendances)

    headers = ["Métrica", "Valor"]
    rows = list(stat_rows)
    for rank, (operator_name, count, avg_duration) in enumerate(productivity_rows[:3], start=1):
        rows.append([f"Top {rank} — Operador", f"{operator_name} ({count} atendimentos, média {avg_duration}s)"])
    return "Resumo Executivo", headers, rows
