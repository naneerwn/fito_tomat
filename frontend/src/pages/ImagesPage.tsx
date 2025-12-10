import { FormEvent, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import type { Greenhouse, Section } from '../types/infrastructure';
import type { ImageItem } from '../types/image';
import './ImagesPage.css';

const mediaHost = import.meta.env.VITE_MEDIA_BASE ?? 'http://127.0.0.1:8000';

const extractResults = <T,>(payload: any): T[] => {
  if (!payload) {
    return [];
  }
  return payload.results ?? payload;
};

interface MLModel {
  value: string;
  label: string;
  description: string;
}

export function ImagesPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [selectedGreenhouse, setSelectedGreenhouse] = useState<string>('');
  const [selectedSection, setSelectedSection] = useState<string>('');
  const [file, setFile] = useState<File | null>(null);
  const [cameraId, setCameraId] = useState('');
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [uploadSuccess, setUploadSuccess] = useState(false);

  const { data: greenhouses = [] } = useQuery<Greenhouse[]>({
    queryKey: ['greenhouses'],
    queryFn: async () => {
      const { data } = await api.get('/greenhouses/');
      return extractResults<Greenhouse>(data);
    },
  });

  const { data: sections = [] } = useQuery<Section[]>({
    queryKey: ['sections'],
    queryFn: async () => {
      const { data } = await api.get('/sections/');
      return extractResults<Section>(data);
    },
  });

  const { data: images = [], isFetching } = useQuery<ImageItem[]>({
    queryKey: ['images'],
    queryFn: async () => {
      const { data } = await api.get('/images/');
      return extractResults<ImageItem>(data);
    },
  });

  const { data: availableModels = [] } = useQuery<MLModel[]>({
    queryKey: ['available-models'],
    queryFn: async () => {
      const { data } = await api.get('/images/available-models/');
      return data.models || [];
    },
  });

  const filteredSections = useMemo(() => {
    if (!selectedGreenhouse) {
      return sections;
    }
    return sections.filter((section) => section.greenhouse === Number(selectedGreenhouse));
  }, [sections, selectedGreenhouse]);

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!file || !selectedSection) {
        throw new Error('Не выбран файл или секция');
      }
      const formData = new FormData();
      formData.append('file_path', file);
      formData.append('file_format', file.name.split('.').pop() ?? file.type);
      formData.append('section', selectedSection);
      if (cameraId) {
        formData.append('camera_id', cameraId);
      }
      if (selectedModel) {
        formData.append('model_type', selectedModel);
      }
      return api.post('/images/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },
    onSuccess: () => {
      setFile(null);
      setCameraId('');
      setSelectedModel('');
      setUploadSuccess(true);
      queryClient.invalidateQueries({ queryKey: ['images'] });
    },
  });

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    uploadMutation.mutate();
  };

  return (
    <section className="images-page">
      <div className="page-header">
        <div>
          <h1>Изображения</h1>
          <p>Загрузка новых снимков и просмотр истории диагностики.</p>
        </div>
      </div>

      <div className="images-layout">
        <form className="upload-card" onSubmit={handleSubmit}>
          <h2>Загрузка изображения</h2>
          <label>
            Теплица
            <select
              value={selectedGreenhouse}
              onChange={(e) => {
                setSelectedGreenhouse(e.target.value);
                setSelectedSection('');
              }}
            >
              <option value="">Выберите теплицу</option>
              {greenhouses.map((gh) => (
                <option key={gh.id} value={gh.id}>
                  {gh.name} ({gh.location})
                </option>
              ))}
            </select>
          </label>

          <label>
            Секция
            <select value={selectedSection} onChange={(e) => setSelectedSection(e.target.value)}>
              <option value="">Выберите секцию</option>
              {filteredSections.map((section) => (
                <option key={section.id} value={section.id}>
                  {section.name}
                </option>
              ))}
            </select>
          </label>

          <label>
            Камера (опционально)
            <input value={cameraId} onChange={(e) => setCameraId(e.target.value)} placeholder="CAM-01" />
          </label>

          <label>
            ML-модель для диагностики
            <select value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)}>
              <option value="">По умолчанию (из настроек)</option>
              {availableModels.map((model) => (
                <option key={model.value} value={model.value} title={model.description}>
                  {model.label}
                </option>
              ))}
            </select>
            {selectedModel && (
              <small style={{ color: '#64748b', fontSize: '12px', marginTop: '4px', display: 'block' }}>
                {availableModels.find((m) => m.value === selectedModel)?.description}
              </small>
            )}
          </label>

          <label className="file-input">
            Файл изображения
            <input type="file" accept="image/*" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          </label>

          {uploadMutation.isError && (
            <p className="error">Ошибка загрузки. Проверьте файл и заполненные поля.</p>
          )}

          {uploadSuccess && (
            <div className="upload-success">
              <p>Фото загружено. Диагностика запускается автоматически.</p>
              <button type="button" onClick={() => navigate('/diagnoses')}>
                Перейти к диагностике
              </button>
            </div>
          )}

          <button type="submit" disabled={!file || !selectedSection || uploadMutation.isLoading}>
            {uploadMutation.isLoading ? 'Загрузка...' : 'Загрузить'}
          </button>
        </form>

        <div className="gallery-card">
          <div className="gallery-header">
            <div>
              <h2>История загрузок</h2>
              <p>Отображаются последние 20 изображений</p>
            </div>
            <button type="button" onClick={() => queryClient.invalidateQueries({ queryKey: ['images'] })}>
              Обновить
            </button>
          </div>

          {isFetching ? (
            <p>Загрузка...</p>
          ) : images.length === 0 ? (
            <p>Пока нет загруженных изображений.</p>
          ) : (
            <div className="gallery-grid">
              {images.map((image) => {
                const section = sections.find((s) => s.id === (typeof image.section === 'number' ? image.section : image.section.id));
                return (
                  <article key={image.id}>
                    <div className="thumb">
                      <img 
                        src={image.image_url || `${mediaHost}${image.file_path}`} 
                        alt={`Снимок ${image.id}`}
                        onError={(e) => {
                          // Fallback если image_url не работает
                          const target = e.target as HTMLImageElement;
                          if (!target.src.includes(mediaHost)) {
                            target.src = `${mediaHost}${image.file_path}`;
                          }
                        }}
                      />
                    </div>
                    <header>
                      <strong>#{image.id}</strong>
                      <span>{section?.name ?? 'Секция'}</span>
                    </header>
                    <p className="meta">
                      Загрузено: {new Date(image.uploaded_at ?? image.timestamp).toLocaleString('ru-RU')}
                    </p>
                    <p className="meta">Формат: {image.file_format.toUpperCase()}</p>
                  </article>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

