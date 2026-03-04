import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from surveys.models import Question


class Command(BaseCommand):
    help = "Import question bank from CSV file."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Path to CSV file.")
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Delete all existing questions before import.",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"]).expanduser().resolve()
        replace = options["replace"]

        if not csv_path.exists() or not csv_path.is_file():
            raise CommandError(f"CSV file not found: {csv_path}")

        valid_categories = set(Question.Category.values)
        required_columns = {"text", "category"}

        created = 0
        updated = 0

        with csv_path.open("r", encoding="utf-8", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            if reader.fieldnames is None:
                raise CommandError("CSV is empty or missing header row.")

            missing_columns = required_columns - set(reader.fieldnames)
            if missing_columns:
                missing = ", ".join(sorted(missing_columns))
                raise CommandError(f"CSV missing required columns: {missing}")

            with transaction.atomic():
                if replace:
                    Question.objects.all().delete()

                for row_index, row in enumerate(reader, start=2):
                    text = (row.get("text") or "").strip()
                    category = (row.get("category") or "").strip().lower()
                    is_active_raw = (row.get("is_active") or "true").strip().lower()

                    if not text:
                        raise CommandError(f"Row {row_index}: 'text' cannot be empty.")
                    if category not in valid_categories:
                        allowed = ", ".join(sorted(valid_categories))
                        raise CommandError(
                            f"Row {row_index}: invalid category '{category}'. "
                            f"Allowed: {allowed}."
                        )

                    if is_active_raw in {"1", "true", "yes", "y"}:
                        is_active = True
                    elif is_active_raw in {"0", "false", "no", "n"}:
                        is_active = False
                    else:
                        raise CommandError(
                            f"Row {row_index}: invalid is_active '{is_active_raw}'. "
                            "Use true/false."
                        )

                    _, was_created = Question.objects.update_or_create(
                        text=text,
                        category=category,
                        defaults={"is_active": is_active},
                    )
                    if was_created:
                        created += 1
                    else:
                        updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Import completed. Created: {created}, Updated: {updated}, Replace mode: {replace}."
            )
        )
