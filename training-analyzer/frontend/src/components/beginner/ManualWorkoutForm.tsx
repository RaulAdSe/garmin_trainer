'use client';

import { useState, useCallback, type FormEvent } from 'react';
import { useTranslations } from 'next-intl';
import { clsx } from 'clsx';
import { Input, Textarea, Select } from '../ui/Input';
import { Button } from '../ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../ui/Card';
import { RPEScale, RPEScaleCompact } from './RPEScale';

export interface ManualWorkoutData {
  date: string;
  durationMin: number;
  distanceKm?: number;
  rpe: number;
  activityType: string;
  name?: string;
  notes?: string;
}

export interface ManualWorkoutFormProps {
  onSubmit: (data: ManualWorkoutData) => Promise<void>;
  onCancel?: () => void;
  initialData?: Partial<ManualWorkoutData>;
  isLoading?: boolean;
  compact?: boolean;
  className?: string;
}

const ACTIVITY_TYPES = [
  'running',
  'cycling',
  'swimming',
  'walking',
  'hiking',
  'strength',
  'yoga',
  'other',
] as const;

export function ManualWorkoutForm({
  onSubmit,
  onCancel,
  initialData,
  isLoading = false,
  compact = false,
  className,
}: ManualWorkoutFormProps) {
  const t = useTranslations('manualWorkout');
  const tCommon = useTranslations('common');

  // Form state
  const [date, setDate] = useState(
    initialData?.date || new Date().toISOString().split('T')[0]
  );
  const [durationMin, setDurationMin] = useState(
    initialData?.durationMin?.toString() || ''
  );
  const [distanceKm, setDistanceKm] = useState(
    initialData?.distanceKm?.toString() || ''
  );
  const [rpe, setRpe] = useState<number | undefined>(initialData?.rpe);
  const [activityType, setActivityType] = useState(
    initialData?.activityType || 'running'
  );
  const [name, setName] = useState(initialData?.name || '');
  const [notes, setNotes] = useState(initialData?.notes || '');

  // Validation state
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  const validateField = useCallback(
    (fieldName: string, value: unknown): string | undefined => {
      switch (fieldName) {
        case 'date':
          if (!value) return t('errors.dateRequired');
          break;
        case 'durationMin':
          const duration = Number(value);
          if (!value || isNaN(duration)) return t('errors.durationRequired');
          if (duration < 1) return t('errors.durationTooShort');
          if (duration > 720) return t('errors.durationTooLong');
          break;
        case 'distanceKm':
          if (value) {
            const distance = Number(value);
            if (isNaN(distance) || distance < 0)
              return t('errors.distanceInvalid');
            if (distance > 500) return t('errors.distanceTooLong');
          }
          break;
        case 'rpe':
          if (!value) return t('errors.rpeRequired');
          break;
        case 'activityType':
          if (!value) return t('errors.activityTypeRequired');
          break;
      }
      return undefined;
    },
    [t]
  );

  const validateForm = useCallback((): boolean => {
    const newErrors: Record<string, string> = {};

    const dateError = validateField('date', date);
    if (dateError) newErrors.date = dateError;

    const durationError = validateField('durationMin', durationMin);
    if (durationError) newErrors.durationMin = durationError;

    const distanceError = validateField('distanceKm', distanceKm);
    if (distanceError) newErrors.distanceKm = distanceError;

    const rpeError = validateField('rpe', rpe);
    if (rpeError) newErrors.rpe = rpeError;

    const activityError = validateField('activityType', activityType);
    if (activityError) newErrors.activityType = activityError;

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [date, durationMin, distanceKm, rpe, activityType, validateField]);

  const handleBlur = useCallback(
    (fieldName: string) => {
      setTouched((prev) => ({ ...prev, [fieldName]: true }));
      const value =
        fieldName === 'date'
          ? date
          : fieldName === 'durationMin'
          ? durationMin
          : fieldName === 'distanceKm'
          ? distanceKm
          : fieldName === 'rpe'
          ? rpe
          : activityType;
      const error = validateField(fieldName, value);
      setErrors((prev) => ({
        ...prev,
        [fieldName]: error || '',
      }));
    },
    [date, durationMin, distanceKm, rpe, activityType, validateField]
  );

  const handleSubmit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();

      // Mark all fields as touched
      setTouched({
        date: true,
        durationMin: true,
        distanceKm: true,
        rpe: true,
        activityType: true,
      });

      if (!validateForm()) {
        return;
      }

      const workoutData: ManualWorkoutData = {
        date,
        durationMin: Number(durationMin),
        distanceKm: distanceKm ? Number(distanceKm) : undefined,
        rpe: rpe!,
        activityType,
        name: name || undefined,
        notes: notes || undefined,
      };

      await onSubmit(workoutData);
    },
    [
      date,
      durationMin,
      distanceKm,
      rpe,
      activityType,
      name,
      notes,
      validateForm,
      onSubmit,
    ]
  );

  const formContent = (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Activity Name (optional) */}
      <Input
        label={t('name')}
        placeholder={t('namePlaceholder')}
        value={name}
        onChange={(e) => setName(e.target.value)}
        disabled={isLoading}
        hint={t('nameHint')}
      />

      {/* Date */}
      <Input
        type="date"
        label={t('date')}
        value={date}
        onChange={(e) => setDate(e.target.value)}
        onBlur={() => handleBlur('date')}
        error={touched.date ? errors.date : undefined}
        disabled={isLoading}
        required
      />

      {/* Activity Type */}
      <Select
        label={t('activityType')}
        value={activityType}
        onChange={(e) => setActivityType(e.target.value)}
        onBlur={() => handleBlur('activityType')}
        error={touched.activityType ? errors.activityType : undefined}
        disabled={isLoading}
        required
      >
        {ACTIVITY_TYPES.map((type) => (
          <option key={type} value={type}>
            {t(`activityTypes.${type}`)}
          </option>
        ))}
      </Select>

      {/* Duration and Distance row */}
      <div className="grid grid-cols-2 gap-4">
        <Input
          type="number"
          label={t('duration')}
          placeholder={t('durationPlaceholder')}
          value={durationMin}
          onChange={(e) => setDurationMin(e.target.value)}
          onBlur={() => handleBlur('durationMin')}
          error={touched.durationMin ? errors.durationMin : undefined}
          disabled={isLoading}
          required
          min={1}
          max={720}
          hint={t('durationHint')}
        />

        <Input
          type="number"
          label={t('distance')}
          placeholder={t('distancePlaceholder')}
          value={distanceKm}
          onChange={(e) => setDistanceKm(e.target.value)}
          onBlur={() => handleBlur('distanceKm')}
          error={touched.distanceKm ? errors.distanceKm : undefined}
          disabled={isLoading}
          step={0.1}
          min={0}
          max={500}
          hint={t('distanceHint')}
        />
      </div>

      {/* RPE Scale */}
      <div className="space-y-1.5">
        <label className="block text-sm font-medium text-gray-300">
          {t('rpe')} <span className="text-red-400">*</span>
        </label>
        {compact ? (
          <RPEScaleCompact
            value={rpe}
            onChange={setRpe}
            disabled={isLoading}
          />
        ) : (
          <RPEScale
            value={rpe}
            onChange={setRpe}
            disabled={isLoading}
            showDetails={true}
            size="md"
          />
        )}
        {touched.rpe && errors.rpe && (
          <p className="text-sm text-red-400" role="alert">
            {errors.rpe}
          </p>
        )}
      </div>

      {/* Notes */}
      <Textarea
        label={t('notes')}
        placeholder={t('notesPlaceholder')}
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        disabled={isLoading}
        rows={3}
        hint={t('notesHint')}
      />

      {/* Estimated Load Preview */}
      {rpe && durationMin && Number(durationMin) > 0 && (
        <div className="p-3 rounded-lg bg-gray-800 border border-gray-700">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-400">{t('estimatedLoad')}</span>
            <span className="font-semibold text-teal-400">
              {Math.round(Number(durationMin) * rpe * 0.8)} {t('loadUnits')}
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            {t('loadExplanation')}
          </p>
        </div>
      )}

      {/* Submit buttons */}
      <div className="flex gap-3 pt-2">
        {onCancel && (
          <Button
            type="button"
            variant="outline"
            onClick={onCancel}
            disabled={isLoading}
            className="flex-1"
          >
            {tCommon('cancel')}
          </Button>
        )}
        <Button
          type="submit"
          variant="primary"
          isLoading={isLoading}
          disabled={isLoading}
          className={onCancel ? 'flex-1' : 'w-full'}
        >
          {isLoading ? t('submitting') : t('submit')}
        </Button>
      </div>
    </form>
  );

  if (compact) {
    return <div className={className}>{formContent}</div>;
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{t('title')}</CardTitle>
        <CardDescription>{t('subtitle')}</CardDescription>
      </CardHeader>
      <CardContent>{formContent}</CardContent>
    </Card>
  );
}

export default ManualWorkoutForm;
